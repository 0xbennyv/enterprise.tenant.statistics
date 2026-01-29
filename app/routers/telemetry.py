# app/routers/telemetry.py

from http.client import HTTPException
import os
from fastapi import APIRouter, Query, Query
from fastapi.responses import FileResponse
from datetime import date, datetime, time, timezone
from app.services.api_clients.alerts_api import AlertsApiClient
from app.services.telemetry.alert_service import AlertTelemetryService
from app.services.api_clients.cases_api import CasesApiClient
from app.services.telemetry.case_service import CaseTelemetryService
from app.services.token_manager import TokenManager
from app.core.constants import oauth_url, global_url
from app.services.api_clients.org_api import OrgApiClient
from app.services.api_clients.case_detections_api import CaseDetectionsApiClient
from app.services.telemetry.mttd_service import MTTDService
from app.services.telemetry.mtta_service import MTTAService
from app.services.telemetry.mttr_service import MTTRService
from app.services.api_clients.health_check_api import HealthCheckApiClient
from app.services.telemetry.endpoint_health_service import EndpointHealthService
from app.core.database import get_worker_db, get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from app.core.queue import telemetry_queue
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
    # created_after: datetime = Query(...),
    # created_before: datetime = Query(...),
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
    # created_after: datetime = Query(...),
    # created_before: datetime = Query(...),
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
    # created_after: datetime = Query(...),
    # created_before: datetime = Query(...),
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
    # created_after: datetime = Query(...),
    # created_before: datetime = Query(...),
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

# @router.get("/cases")
# async def case_telemetry(
#     created_after: datetime = Query(...),
#     created_before: datetime = Query(...),
# ):
#     """
#     Collects case telemetry between created_after and created_before.
#     Returns Number of Cases Created and Number of Cases Resolved.
#     """
#     return await case_service.collect__metrics(
#         created_after, created_before
#     )

# @router.get("/csv")
# async def get_telemetry_csv():
#     """
#     Collects telemetry for last 30 days and returns a CSV file for download.
#     """
#     from_time, to_time = last_n_days_range(30)

#     telemetry = await collect_telemetry(token_manager, from_time, to_time)
#     csv_str = generate_telemetry_csv(telemetry)

#     # Convert CSV string to bytes for StreamingResponse
#     buffer = BytesIO()
#     buffer.write(csv_str.encode("utf-8"))
#     buffer.seek(0)

#     return StreamingResponse(
#         buffer,
#         media_type="text/csv",
#         headers={"Content-Disposition": "attachment; filename=telemetry.csv"}
#     )

# @router.get("/export")
# async def export_telemetry(
#     date_from: date = Query(...),
#     date_to: date = Query(...),
# ):
#     service = TelemetryExportService(
#         alert_service=alerts_service,
#         case_sla_service=case_service,
#         mttd_service=mttd_service,
#         mtta_service=mtta_service,
#         mttr_service=mttr_service,
#         endpoint_health_service=endpoint_health_service,
#     )
#     # service = TelemetryExportService()
#     content = await service.export(date_from, date_to)

#     filename = f"{date_from}_to_{date_to}.xlsx"

#     return StreamingResponse(
#         iter([content]),
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         headers={
#             "Content-Disposition": f'attachment; filename="{filename}"'
#         },
#     )

@router.post("/exports")
async def export_telemetry(date_from: str, date_to: str, db: AsyncSession = Depends(get_db)):
    job_id = str(uuid4())

    # Insert job in DB
    await db.execute(
        insert(ExportJob).values(
            id=job_id,
            date_from=date_from,
            date_to=date_to,
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
