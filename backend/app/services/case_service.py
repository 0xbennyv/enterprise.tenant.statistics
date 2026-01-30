# app/services/case_service.py

import asyncio
from datetime import date, datetime
from typing import Dict, Any

from app.api.org_api import OrgApiClient
from app.api.cases_api import CasesApiClient
from app.aggregator.case_aggregator import CaseTelemetryAggregator


class CaseTelemetryService:
    def __init__(
        self,
        org_client: OrgApiClient,
        cases_client: CasesApiClient,
    ):
        self.org_client = org_client
        self.cases_client = cases_client

    async def collect_sla_metrics(
        self,
        created_after: datetime,
        created_before: datetime,
        # date_from: date,
        # date_to: date,
    ) -> Dict[str, Any]:
        tenants = await self.org_client.list_tenants()

        async def fetch_cases(tenant):
            return tenant["id"], tenant["name"], await self.cases_client.list_cases(
                api_host=tenant["apiHost"],
                tenant_id=tenant["id"],
                # created_after=(date_from and datetime.combine(date_from, datetime.min.time())),
                # created_before=(date_to and datetime.combine(date_to, datetime.max.time())),
                created_after=created_after,
                created_before=created_before,
                status="resolved",
            )

        results = await asyncio.gather(
            *[fetch_cases(t) for t in tenants]
        )

        cases_by_tenant = {
            (tenant_id, tenant_name): cases
            for tenant_id, tenant_name, cases in results
        }

        return CaseTelemetryAggregator.aggregate(cases_by_tenant)
    
    async def collect_case_metrics(
        self,
        created_after: datetime,
        created_before: datetime,
    ) -> Dict[str, Any]:
        tenants = await self.org_client.list_tenants()

        async def fetch_cases(tenant):
            return tenant["id"], tenant["name"], await self.cases_client.list_cases(
                api_host=tenant["apiHost"],
                tenant_id=tenant["id"],
                created_after=created_after,
                created_before=created_before,
                # IMPORTANT: no status filter
            )

        results = await asyncio.gather(
            *[fetch_cases(t) for t in tenants]
        )

        cases_by_tenant = {
            (tenant_id, tenant_name): cases
            for tenant_id, tenant_name, cases in results
        }

        return CaseTelemetryAggregator.aggregate(cases_by_tenant)
