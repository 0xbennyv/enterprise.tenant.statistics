# app/routers/telemetry.py

import os
from fastapi import APIRouter, Query
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
from app.services.redis_queue import telemetry_queue
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
