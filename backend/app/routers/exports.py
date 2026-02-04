# app/routers/exports.py

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from datetime import datetime
from app.api.alerts_api import AlertsApiClient
from app.services.alert_service import AlertTelemetryService
from app.api.cases_api import CasesApiClient
from app.services.case_service import CaseTelemetryService
from app.api.oauth_api import TokenManager
from app.core.constants import oauth_url, global_url
from app.api.org_api import OrgApiClient
from app.api.case_detections_api import CaseDetectionsApiClient
from app.services.mttd_service import MTTDService
from app.services.mtta_service import MTTAService
from app.services.mttr_service import MTTRService
from app.api.health_check_api import HealthCheckApiClient
from app.services.endpoint_health_service import EndpointHealthService
from app.core.database import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from app.services.redis_queue import telemetry_queue, started, finished, failed, serialize_job
from app.models.export_job import ExportJob
from sqlalchemy import insert, select
import logging

from app.services.export_job_service import update_job_status
from app.workers.telemetry_export_sync import run_export_sync

logger = logging.getLogger("app.exports")

router = APIRouter()

@router.post("/")
async def export_telemetry(date_from: str, date_to: str, db: AsyncSession = Depends(get_db)):
    date_from_new = datetime.strptime(date_from, "%Y-%m-%d").date()
    date_to_new = datetime.strptime(date_to, "%Y-%m-%d").date()

    # Check if there is already a record with same date_from and date_to
    exists = await db.execute(
        ExportJob.__table__.select().where(
            ExportJob.date_from == date_from_new,
            ExportJob.date_to == date_to_new
        )
    )
    if exists.first():
        raise HTTPException(status_code=404, detail="Job already exists")

    # Enqueue RQ job (sync wrapper handles async)
    job = telemetry_queue.enqueue(
        run_export_sync, 
        date_from, 
        date_to,
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
            status=job._status,
            progress={
                "stage": "queued",
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
async def get_exports(db: AsyncSession = Depends(get_db)):
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
    all_jobs = []

    # 1. Jobs still in queue (safe)
    for job in telemetry_queue.get_jobs():
        all_jobs.append(serialize_job(job))

    # 2. Started jobs (UNSAFE without guard)
    try:
        for job_id in started.get_job_ids():
            job = telemetry_queue.fetch_job(job_id)
            if job:
                all_jobs.append(serialize_job(job))
    except ValueError as e:
        logger.warning("Skipping corrupt started job execution: %s", e)

    # 3. Finished jobs
    try:
        for job_id in finished.get_job_ids():
            job = telemetry_queue.fetch_job(job_id)
            if job:
                all_jobs.append(serialize_job(job))
    except ValueError as e:
        logger.warning("Skipping corrupt finished job execution: %s", e)

    # 4. Failed jobs
    try:
        for job_id in failed.get_job_ids():
            job = telemetry_queue.fetch_job(job_id)
            if job:
                all_jobs.append(serialize_job(job))
    except ValueError as e:
        logger.warning("Skipping corrupt failed job execution: %s", e)

    # Order safely
    all_jobs.sort(
        key=lambda x: x.get("enqueued_at") or datetime.min,
        reverse=True,
    )

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
        "status": job["status"],
        "progress": job.get("progress"),
        "file_path": job.get("file_path"),
        "error": job.get("error"),
    }


# ---------- Cancel a running job ----------
@router.post("/{job_id}/cancel")
async def cancel_export(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        ExportJob.__table__.select().where(ExportJob.job_id == job_id)
    )
    job_row = result.first()

    if not job_row:
        raise HTTPException(status_code=404, detail="Job not found")
    
    await update_job_status(
        db,
        job_id,
        new_status="cancelling",
        progress={"stage": "cancelling"},
    )
    return {"status": "cancelling"}

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
