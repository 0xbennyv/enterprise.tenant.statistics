# app/routers/exports.py

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from datetime import datetime
from app.core.database import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from app.services.redis_queue import telemetry_queue, started, finished, failed, serialize_job
from app.models.export_job import ExportJob
from sqlalchemy import insert, select
import logging
from rq.job import Job
from rq.exceptions import NoSuchJobError
from app.services.export_job_service import update_job_status, _apply_job_status_update
from app.workers.telemetry_export_sync import run_export_sync

logger = logging.getLogger("app.exports")

router = APIRouter()

@router.post("/")
async def export_telemetry(
    date_from: str, 
    date_to: str, 
    tenant_id: Optional[str] = Query(default=None), 
    db: AsyncSession = Depends(get_db)
):
    date_from_new = datetime.strptime(date_from, "%Y-%m-%d").date()
    date_to_new = datetime.strptime(date_to, "%Y-%m-%d").date()

    # Check if there is already a record with same date_from and date_to
    if tenant_id:
        exists = await db.execute(
            ExportJob.__table__.select().where(
                ExportJob.date_from == date_from_new,
                ExportJob.date_to == date_to_new,
                ExportJob.tenant_id == tenant_id
            )
        )
    else:
        exists = await db.execute(
            ExportJob.__table__.select().where(
                ExportJob.date_from == date_from_new,
                ExportJob.date_to == date_to_new,
                ExportJob.tenant_id == None
            )
        )
    if exists.first():
        raise HTTPException(status_code=404, detail="Job already exists")

    # Enqueue RQ job (sync wrapper handles async)
    job = telemetry_queue.enqueue(
        run_export_sync, 
        date_from, 
        date_to,
        tenant_id,
        job_timeout=60 * 60 * 2,  # example: 2h
        result_ttl=0,
        failure_ttl=0,
    )

    # Insert job in DB
    await db.execute(
        insert(ExportJob).values(
            job_id=job.id,
            date_from=date_from_new,
            date_to=date_to_new,
            tenant_id=tenant_id,
            status=job._status,
            progress={
                "stage": "Queued",
            },
        )
    )
    await db.commit()

    return {
        # "id": job_id, 
        "job_id": job.id,
        "status": job._status,
    }

@router.get("/")
async def get_exports(tenant_id: Optional[str] = Query(default=None), db: AsyncSession = Depends(get_db)):
    if tenant_id:
        result = await db.execute(
            ExportJob.__table__.select().where(ExportJob.tenant_id == tenant_id).order_by(ExportJob.created_at.desc())
        )
    else:
        result = await db.execute(
            ExportJob.__table__.select().order_by(ExportJob.created_at.desc())
        )
    jobs = result.all()

    return [
        {
            "id": job._mapping["id"],
            "job_id": job._mapping["job_id"],
            "date_from": job._mapping["date_from"],
            "date_to": job._mapping["date_to"],
            "tenant_id": job._mapping["tenant_id"],
            "status": job._mapping["status"],
            "progress": job._mapping.get("progress"),
            "file_path": job._mapping.get("file_path"),
            "error": job._mapping.get("error"),
            "created_at": job._mapping.get("created_at"),
        }
        for job in jobs
    ]

@router.get("/jobs/redis")
async def get_export_jobs_in_redis():
    """
    Get all export jobs currently in the RQ queue.
    """

    all_jobs = []

    # Jobs still in queue
    for job in telemetry_queue.get_jobs():
        all_jobs.append(serialize_job(job))

    # Jobs currently running
    for job_id in started.get_job_ids():
        job = telemetry_queue.fetch_job(job_id)
        all_jobs.append(serialize_job(job))

    # Jobs finished
    for job_id in finished.get_job_ids():
        job = telemetry_queue.fetch_job(job_id)
        all_jobs.append(serialize_job(job))

    # Jobs failed
    for job_id in failed.get_job_ids():
        job = telemetry_queue.fetch_job(job_id)
        all_jobs.append(serialize_job(job))

    # Order by enqueued_at descending
    all_jobs.sort(key=lambda x: x["enqueued_at"] or datetime.min, reverse=True)

    return all_jobs


# ---------- Get status of a job ----------
@router.get("/{job_id}")
async def get_export_status(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        ExportJob.__table__.select().where(ExportJob.job_id == job_id)
    )
    job_row = result.first()

    if not job_row:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_row._mapping
    return {
        "job_id": job_id,
        "date_from": job["date_from"],
        "date_to": job["date_to"],
        "tenant_id": job["tenant_id"],
        "status": job["status"],
        "progress": job.get("progress"),
        "file_path": job.get("file_path"),
        "error": job.get("error"),
    }


# ---------- Cancel a running job ----------
@router.post("/{job_id}/cancel")
async def cancel_export(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Cancel an export job.
    - Queued: removed immediately
    - Running: cooperative cancel (worker checks DB)
    - Missing: treated as cancelled
    """
    # Fetch job from DB
    result = await db.execute(
        ExportJob.__table__.select().where(
            ExportJob.job_id == job_id,
            ExportJob.status.in_(["queued", "running"])
        )
    )
    job_row = result.first()
    if not job_row:
        raise HTTPException(status_code=404, detail="Job not found or not cancellable")

    # Attempt to fetch RQ job
    try:
        rq_job = Job.fetch(job_id, connection=telemetry_queue.connection)
    except NoSuchJobError:
        rq_job = None

    if rq_job:
        status = rq_job.get_status()
        if status == "queued":
            # Remove immediately
            telemetry_queue.remove(job_id)
            job = await update_job_status(
                db,
                job_id,
                new_status="cancelled",
                progress={"stage": "Cancelled"},
            )
        elif status == "started":
            # Running: cooperative cancel
            job = await update_job_status(
                db,
                job_id,
                new_status="cancelling",
                progress={"stage": "Cancelling..."},
            )
        else:
            # Other states cannot cancel
            raise HTTPException(
                status_code=409,
                detail=f"Cannot cancel job in state: {status}",
            )
    else:
        # Job missing in queue: treat as cancelled
        job = await update_job_status(
            db,
            job_id,
            new_status="cancelled",
            progress={"stage": "Cancelled"},
        )
    await db.commit()
    return job


@router.get("/{job_id}/download")
async def download_export(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Download the completed export file on the browser
    or thru Postman
    """
    result = await db.execute(
        ExportJob.__table__.select().where(ExportJob.job_id == job_id)
    )
    job_row = result.first()

    if not job_row or job_row._mapping["status"] != "completed":
        raise HTTPException(status_code=404, detail="File not ready")

    file_path = job_row._mapping["file_path"]
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path, 
        filename=os.path.basename(file_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.delete("/{job_id}")
async def delete_export(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete the file and export metadata from the db.
    Works both locally and inside Docker if paths are correctly mounted.
    """
    # Fetch job
    result = await db.execute(
        ExportJob.__table__.select().where(ExportJob.job_id == job_id)
    )
    job_row = result.first()

    if not job_row:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_row._mapping["status"] == "running":
        raise HTTPException(status_code=400, detail="Cannot delete a running job")

    # Delete from RQ queue
    try:
        telemetry_queue.remove(job_row._mapping["job_id"])
    except Exception:
        # Queue might not have it, ignore safely
        pass

    # Delete file
    file_path = job_row._mapping.get("file_path")
    if file_path:
        path = Path(file_path)
        if path.exists():
            try:
                path.unlink()  # safer than os.remove
            except PermissionError:
                raise HTTPException(status_code=500, detail="Permission denied deleting file")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

    # Delete from DB
    await db.execute(
        ExportJob.__table__.delete().where(ExportJob.job_id == job_id)
    )
    await db.commit()

    return {"status": "deleted"}
