# app/workers/telemetry_export.py
import asyncio
import traceback
from datetime import datetime
from pathlib import Path

from app.models.export_job import ExportJob
from app.services.export_job_service import update_job_progress_only, update_job_status
from app.services.telemetry.export_service import TelemetryExportService

EXPORT_DIR = Path("/code/exports")  # <-- Docker-mounted volume for persistence
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


# async def run_export(job_id: str, date_from: str, date_to: str):
#     """
#     Main export worker for telemetry.
#     Initializes clients inside the coroutine to avoid loop issues.
#     Uses a single DB session for progress updates and status changes.
#     """
#     print(f"[EXPORT] Job {job_id} STARTED at {datetime.utcnow().isoformat()}")

#     from app.core.database import get_worker_db
#     from app.services.token_manager import TokenManager
#     from app.services.api_clients.org_api import OrgApiClient
#     from app.services.api_clients.alerts_api import AlertsApiClient
#     from app.services.api_clients.case_detections_api import CaseDetectionsApiClient
#     from app.services.api_clients.cases_api import CasesApiClient
#     from app.services.api_clients.health_check_api import HealthCheckApiClient
#     from app.services.telemetry.alert_service import AlertTelemetryService
#     from app.services.telemetry.case_service import CaseTelemetryService
#     from app.services.telemetry.mttd_service import MTTDService
#     from app.services.telemetry.mtta_service import MTTAService
#     from app.services.telemetry.mttr_service import MTTRService
#     from app.services.telemetry.endpoint_health_service import EndpointHealthService
#     from app.core.constants import oauth_url, global_url

#     # Convert string dates to datetime.date
#     date_from_dt = datetime.fromisoformat(date_from).date()
#     date_to_dt = datetime.fromisoformat(date_to).date()

#     # Initialize token manager and API clients inside coroutine
#     token_manager = TokenManager(oauth_url, global_url)
#     org_client = OrgApiClient(token_manager)
#     alerts_client = AlertsApiClient(token_manager)
#     cases_client = CasesApiClient(token_manager)
#     detections_client = CaseDetectionsApiClient(token_manager)
#     endpoint_health_client = HealthCheckApiClient(token_manager)

#     alerts_service = AlertTelemetryService(org_client, alerts_client)
#     case_service = CaseTelemetryService(org_client, cases_client)
#     mttd_service = MTTDService(org_client, cases_client, detections_client)
#     mtta_service = MTTAService(org_client, cases_client)
#     mttr_service = MTTRService(org_client, cases_client)
#     endpoint_health_service = EndpointHealthService(org_client, endpoint_health_client)

#     async with get_worker_db() as db:
#         # 1️⃣ Move job to running
#         await update_job_status(db, job_id, "running", progress={"stage": "starting"})

#         # Progress and cancellation callbacks using single DB session
#         async def is_cancelled_cb() -> bool:
#             result = await db.execute(
#                 ExportJob.__table__.select().where(ExportJob.id == job_id)
#             )
#             job = result.first()
#             return bool(job and job._mapping.get("status") == "cancelling")

#         async def update_progress_cb(progress: dict):
#             await update_job_progress_only(db, job_id, progress)

#         try:
#             # 2️⃣ Initialize export service
#             service = TelemetryExportService(
#                 alert_service=alerts_service,
#                 case_sla_service=case_service,
#                 mttd_service=mttd_service,
#                 mtta_service=mtta_service,
#                 mttr_service=mttr_service,
#                 endpoint_health_service=endpoint_health_service,
#                 # progress_cb=lambda p: asyncio.create_task(update_progress_cb(p)),
#                 progress_cb=update_progress_cb,
#                 is_cancelled_cb=is_cancelled_cb,
#             )

#             # 3️⃣ Run export
#             file_path = await service.export_to_excel(date_from_dt, date_to_dt)

#             if not file_path:
#                 await update_job_status(
#                     db, job_id, "cancelled", progress={"stage": "cancelled"}
#                 )
#                 print(f"[EXPORT] Job {job_id} CANCELLED at {datetime.utcnow().isoformat()}")
#                 return

#             # 4️⃣ Mark job as completed
#             await update_job_status(
#                 db,
#                 job_id,
#                 "completed",
#                 progress={"stage": "done", "percent": 100},
#                 file_path=file_path,
#             )
#             print(f"[EXPORT] Job {job_id} COMPLETED at {datetime.utcnow().isoformat()}")

#         except Exception as e:
#             # 5️⃣ Mark job as failed
#             await update_job_status(
#                 db,
#                 job_id,
#                 "failed",
#                 progress={"stage": "failed", "trace": traceback.format_exc()},
#                 error=str(e),
#             )
#             print(f"[EXPORT] Job {job_id} FAILED at {datetime.utcnow().isoformat()}")
#             print(traceback.format_exc())

async def run_export(job_id: str, date_from: str, date_to: str):
    """
    Telemetry export worker.
    - NO long-lived DB sessions
    - Each DB operation gets its own session
    - Safe for RQ + Windows + async SQLAlchemy
    """

    print(f"[EXPORT] Job {job_id} STARTED at {datetime.utcnow().isoformat()}")

    date_from_dt = datetime.fromisoformat(date_from).date()
    date_to_dt = datetime.fromisoformat(date_to).date()

    # ───────────────────────── helpers ─────────────────────────

    # async def set_status(
    #     status: str,
    #     *,
    #     progress: dict | None = None,
    #     error: str | None = None,
    #     file_path: str | None = None,
    # ):
    #     from app.core.database import get_worker_db

    #     async with get_worker_db() as db:
    #         await update_job_status(
    #             db,
    #             job_id,
    #             status,
    #             progress=progress,
    #             error=error,
    #             file_path=file_path,
    #         )

    async def set_status(
        job_id: str,
        status: str,
        *,
        progress: dict | None = None,
        error: str | None = None,
        file_path: str | None = None,
    ):
        from app.core.database import get_worker_db

        async with get_worker_db() as db:
            await update_job_status(
                db,
                job_id,
                new_status=status,
                progress=progress,
                error=error,
                file_path=file_path,
            )

    async def update_progress(progress: dict):
        from app.core.database import get_worker_db

        async with get_worker_db() as db:
            await update_job_progress_only(db, job_id, progress)

    async def is_cancelled() -> bool:
        from app.core.database import get_worker_db

        async with get_worker_db() as db:
            result = await db.execute(
                ExportJob.__table__.select().where(ExportJob.id == job_id)
            )
            job = result.first()
            return bool(job and job._mapping["status"] == "cancelling")

    # ───────────────────── job execution ──────────────────────

    try:
        # 1️⃣ move job → running
        await set_status(
            job_id=job_id,
            status="running", 
            progress={"stage": "starting"}
        )

        # 2️⃣ create all async clients INSIDE coroutine
        from app.services.token_manager import TokenManager
        from app.services.api_clients.org_api import OrgApiClient
        from app.services.api_clients.alerts_api import AlertsApiClient
        from app.services.api_clients.case_detections_api import CaseDetectionsApiClient
        from app.services.api_clients.cases_api import CasesApiClient
        from app.services.api_clients.health_check_api import HealthCheckApiClient
        from app.services.telemetry.alert_service import AlertTelemetryService
        from app.services.telemetry.case_service import CaseTelemetryService
        from app.services.telemetry.mttd_service import MTTDService
        from app.services.telemetry.mtta_service import MTTAService
        from app.services.telemetry.mttr_service import MTTRService
        from app.services.telemetry.endpoint_health_service import (
            EndpointHealthService,
        )
        from app.core.constants import oauth_url, global_url

        token_manager = TokenManager(oauth_url, global_url)
        org_client = OrgApiClient(token_manager)

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

        mtta_service = MTTAService(org_client, cases_client)
        mttr_service = MTTRService(org_client, cases_client)

        endpoint_health_client = HealthCheckApiClient(token_manager)
        endpoint_health_service = EndpointHealthService(
            org_client, endpoint_health_client
        )

        # 3️⃣ create export service
        service = TelemetryExportService(
            alert_service=alerts_service,
            case_sla_service=case_service,
            mttd_service=mttd_service,
            mtta_service=mtta_service,
            mttr_service=mttr_service,
            endpoint_health_service=endpoint_health_service,
            progress_cb=update_progress,
            is_cancelled_cb=is_cancelled,
        )

        # 4️⃣ run export
        file_path = await service.export_to_excel(date_from_dt, date_to_dt)

        if not file_path:
            await set_status(
                job_id=job_id,
                status="cancelled",
                progress={"stage": "cancelled"},
            )
            print(f"[EXPORT] Job {job_id} CANCELLED")
            return

        # 5️⃣ mark completed
        await set_status(
            job_id=job_id,
            status="completed",
            progress={"stage": "done", "percent": 100},
            file_path=file_path,
        )

        print(f"[EXPORT] Job {job_id} COMPLETED")

    except Exception as exc:
        await set_status(
            job_id=job_id,
            status="failed",
            progress={"stage": "failed"},
            error=str(exc),
        )
        print(f"[EXPORT] Job {job_id} FAILED")
        print(traceback.format_exc())
        raise

# Optional helper for updating progress
async def update_progress(job_id: str, progress: dict):
    from app.core.database import get_worker_db
    from app.services.export_job_service import update_job_progress_only

    async with get_worker_db() as db:
        await update_job_progress_only(db, job_id, progress)


# Optional helper for cooperative cancellation
async def is_cancelled(job_id: str) -> bool:
    from app.core.database import get_worker_db
    from app.models.export_job import ExportJob

    async with get_worker_db() as db:
        result = await db.execute(
            ExportJob.__table__.select().where(ExportJob.id == job_id)
        )
        job = result.first()
        return job and job._mapping.get("status") == "cancelling"
