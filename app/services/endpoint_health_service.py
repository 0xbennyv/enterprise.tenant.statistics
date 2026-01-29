# app/services/telemetry/endpoint_health_service.py

import asyncio
from typing import Dict, Any
from app.api.org_api import OrgApiClient
from app.api.health_check_api import HealthCheckApiClient
from app.aggregator.endpoint_health_aggregator import EndpointHealthAggregator


class EndpointHealthService:
    def __init__(
        self,
        org_client: OrgApiClient,
        endpoint_health_client: HealthCheckApiClient,
    ):
        self.org_client = org_client
        self.endpoint_health_client = endpoint_health_client

    async def collect_endpoint_health(self) -> Dict[str, Any]:
        tenants = await self.org_client.list_tenants()


        async def fetch_health_check(tenant):
            health_check = await self.endpoint_health_client.get_endpoint_health(
                api_host=tenant["apiHost"],
                tenant_id=tenant["id"],
            )
            return tenant["id"], tenant["name"], health_check
        
        results = await asyncio.gather(
            *[fetch_health_check(t) for t in tenants]
        )

        health_by_tenant = {
            (tenant_id, tenant_name): health_check
            for tenant_id, tenant_name, health_check in results
        }

        # health_by_tenant = {
        #     (tenant_id, tenant_name): health
        #     for (tenant_id, tenant_name), health in await self.endpoint_health_client.get_endpoint_health(
        #         api_host=tenant["apiHost"],
        #         tenant_id=tenant["id"],
        #     ) for tenant in tenants
        # }

        # for tenant in tenants:
            # health_by_tenant[tenant["id"]] = await self.endpoint_health_client.get_endpoint_health(
            #     api_host=tenant["apiHost"],
            #     tenant_id=tenant["id"],
            # )

        return EndpointHealthAggregator.aggregate(health_by_tenant)
