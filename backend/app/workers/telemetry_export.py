# app/workers/telemetry_export.py

import traceback
import logging
from datetime import datetime
from pathlib import Path

from app.models.export_job import ExportJob
from app.services.export_job_service import update_job_progress_only, update_job_status
from app.services.export_service import TelemetryExportService

logger = logging.getLogger("app.telemetry_export")

EXPORT_DIR = Path("/code/exports")  # <-- Docker-mounted volume for persistence
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

async def run_export(job_id: str, date_from: str, date_to: str, tenant_id: str | None):
    """
    Telemetry export worker.
    - NO long-lived DB sessions
    - Each DB operation gets its own session
    - Safe for RQ + Windows + async SQLAlchemy
    """

    print(f"[EXPORT] Job {job_id} STARTED at {datetime.utcnow().isoformat()}")

    date_from_dt = datetime.fromisoformat(date_from).date()
    date_to_dt = datetime.fromisoformat(date_to).date()

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
                ExportJob.__table__.select().where(ExportJob.job_id == job_id)
            )
            job = result.first()
            return bool(job and job._mapping["status"] == "cancelling")

    # ───────────────────── job execution ──────────────────────

    try:
        # move job → running
        await set_status(
            job_id=job_id,
            status="running", 
            progress={"stage": "starting"}
        )

        # create all async clients INSIDE coroutine
        from app.api.oauth_api import TokenManager
        from app.api.org_api import OrgApiClient
        from app.api.alerts_api import AlertsApiClient
        from app.api.case_detections_api import CaseDetectionsApiClient
        from app.api.cases_api import CasesApiClient
        from app.api.health_check_api import HealthCheckApiClient
        from app.services.alert_service import AlertTelemetryService
        from app.services.case_service import CaseTelemetryService
        from app.services.mttd_service import MTTDService
        from app.services.mtta_service import MTTAService
        from app.services.mttr_service import MTTRService
        from app.services.endpoint_health_service import (
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

        # create export service
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

        # run export
        file_path = await service.export_to_excel(date_from_dt, date_to_dt, tenant_id)

        if not file_path:
            await set_status(
                job_id=job_id,
                status="cancelled",
                progress={"stage": "cancelled"},
            )
            print(f"[EXPORT] Job {job_id} CANCELLED")
            return

        # mark completed
        await set_status(
            job_id=job_id,
            status="completed",
            progress={"stage": "done", "percent": 100},
            error=None,
            file_path=file_path,
        )

        print(f"[EXPORT] Job {job_id} COMPLETED")
    except Exception as exc:
        try:
            await set_status(job_id, "failed", error=str(exc))
        except ValueError:
            # Job already failed — do not explode
            logger.warning("Job %s already marked failed", job_id)
        raise

# Optional helper for updating progress
async def update_progress(job_id: str, progress: dict):
    from app.core.database import get_worker_db
    from app.services.export_job_service import update_job_progress_only

    async with get_worker_db() as db:
        await update_job_progress_only(db, job_id, progress)
