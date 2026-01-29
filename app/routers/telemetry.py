# app/routers/telemetry.py

from http.client import HTTPException
import os
from fastapi import APIRouter, Query, Query
from fastapi.responses import FileResponse
from datetime import date, datetime, time, timezone
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
from sqlalchemy import insert


from app.services.export_job_service import update_job_status
from app.workers.telemetry_export_sync import run_export_sync

router = APIRouter()

token_manager = TokenManager(oauth_url, global_url)
org_client = OrgApiClient(token_manager)
# print("ORG CLIENT:", org_client)
alerts_client = AlertsApiClient(token_manager)
alerts_service = AlertTelemetryService(org_client, alerts_client)

cases_client = CasesApiClient(token_manager)
case_service = CaseTelemetryService(org_client, cases_client)

detections_client = CaseDetectionsApiClient(token_manager)
mttd_service = MTTDService(
    org_client=org_client,
    cases_client=cases_client,
    detections_client=detections_client,
)

mtta_service = MTTAService(
    org_client=org_client,
    cases_client=cases_client,
)

mttr_service = MTTRService(
    org_client=org_client,
    cases_client=cases_client,
)

endpoint_health_client = HealthCheckApiClient(token_manager)

endpoint_health_service = EndpointHealthService(
    org_client=org_client,
    endpoint_health_client=endpoint_health_client,
)


@router.get("/alerts")
async def alert_telemetry(
    date_from: date = Query(...),
    date_to: date = Query(...)
):
    """
    Collects alert telemetry between date_from and date_to.
    Returns Number of Security Incidents.
    """
    return await alerts_service.collect(date_from, date_to)

@router.get("/cases/sla")
async def cases_sla_telemetry(
    date_from: date = Query(...),
    date_to: date = Query(...)
):
    created_after = datetime.combine(
        date_from, time.min, tzinfo=timezone.utc
    )

    created_before = datetime.combine(
        date_to, time.min, tzinfo=timezone.utc
    )
    
    return await case_service.collect_sla_metrics(
            created_after, created_before
        )

@router.get("/mttd")
async def mean_time_to_detect(
    date_from: date = Query(...),
    date_to: date = Query(...)
):
    created_after = datetime.combine(
        date_from, time.min, tzinfo=timezone.utc
    )

    created_before = datetime.combine(
        date_to, time.min, tzinfo=timezone.utc
    )

    return await mttd_service.collect_mttd(created_after, created_before)

@router.get("/mtta")
async def mean_time_to_acknowledge(
    date_from: date = Query(...),
    date_to: date = Query(...)
):
    created_after = datetime.combine(
        date_from, time.min, tzinfo=timezone.utc
    )

    created_before = datetime.combine(
        date_to, time.min, tzinfo=timezone.utc
    )

    return await mtta_service.collect_mtta(created_after, created_before)

@router.get("/mttr")
async def mean_time_to_recover(
    date_from: date = Query(...),
    date_to: date = Query(...)
):
    created_after = datetime.combine(
        date_from, time.min, tzinfo=timezone.utc
    )

    created_before = datetime.combine(
        date_to, time.min, tzinfo=timezone.utc
    )

    return await mttr_service.collect_mttr(created_after, created_before)

@router.get("/endpoint-health")
async def endpoint_health():
    return await endpoint_health_service.collect_endpoint_health()

@router.post("/exports")
async def export_telemetry(date_from: str, date_to: str, db: AsyncSession = Depends(get_db)):
    job_id = str(uuid4())

    date_from_new = datetime.strptime(date_from, "%Y-%m-%d").date()
    date_to_new = datetime.strptime(date_to, "%Y-%m-%d").date()

    # Insert job in DB
    await db.execute(
        insert(ExportJob).values(
            id=job_id,
            date_from=date_from_new,
            date_to=date_to_new,
            status="queued",
            progress={"stage": "queued"},
        )
    )
    await db.commit()

    # Enqueue RQ job (sync wrapper handles async)
    telemetry_queue.enqueue(run_export_sync, job_id, date_from, date_to)

    return {"job_id": job_id, "status": "queued"}

@router.get("/exports")
async def get_exports(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        ExportJob.__table__.select().order_by(ExportJob.created_at.desc())
    )
    jobs = result.all()

    return [
        {
            "job_id": job._mapping["id"],
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

@router.get("/exports/jobs/redis")
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
@router.get("/exports/{job_id}")
async def get_export_status(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        ExportJob.__table__.select().where(ExportJob.id == job_id)
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
@router.post("/exports/{job_id}/cancel")
async def cancel_export(job_id: str, db: AsyncSession = Depends(get_db)):
    await update_job_status(
        db,
        job_id,
        new_status="cancelling",
        progress={"stage": "cancelling"},
    )
    return {"status": "cancelling"}

@router.get("/exports/{job_id}/download")
async def download_export(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Download the completed export file on the browser
    or thru Postman
    """
    result = await db.execute(
        ExportJob.__table__.select().where(ExportJob.id == job_id)
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
