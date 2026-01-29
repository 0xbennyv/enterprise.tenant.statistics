# app/services/telemetry/mttr_service.py

import asyncio
import datetime
from typing import Dict, Any

from app.services.api_clients.org_api import OrgApiClient
from app.services.api_clients.cases_api import CasesApiClient
from app.services.telemetry.mttr_aggregator import MTTRAggregator


class MTTRService:
    def __init__(
        self,
        org_client: OrgApiClient,
        cases_client: CasesApiClient,
    ):
        self.org_client = org_client
        self.cases_client = cases_client

    async def collect_mttr(
            self,
            created_after: datetime,
            created_before: datetime,
        ) -> Dict[str, Any]:
        tenants = await self.org_client.list_tenants()

        # cases_by_tenant = {}

        # for tenant in tenants:
        #     tenant_id = tenant["id"]
        #     api_host = tenant["apiHost"]

        #     cases = await self.cases_client.list_cases(
        #         api_host=api_host,
        #         tenant_id=tenant_id,
        #         created_after=created_after,
        #         created_before=created_before,
        #         # IMPORTANT: no status filter
        #     )

        #     cases_by_tenant = {
        #         (tenant_id, tenant["name"]): cases
        #         for tenant_id, tenant in [(tenant_id, tenant)]
        #     }

        async def fetch_cases(tenant):
            return tenant["id"], tenant["name"],await self.cases_client.list_cases(
                api_host=tenant["apiHost"],
                tenant_id=tenant["id"],
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

        return MTTRAggregator.aggregate(cases_by_tenant)
