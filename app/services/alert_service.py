# app/services/alert_service.py

import asyncio
from datetime import date
from typing import Dict

from app.api.alerts_api import AlertsApiClient
from app.api.org_api import OrgApiClient
from app.aggregator.alert_aggregator import AlertTelemetryAggregator


class AlertTelemetryService:
    def __init__(self, org_client: OrgApiClient, alerts_client: AlertsApiClient):
        self.org_client = org_client
        self.alerts_client = alerts_client

    async def collect(self, date_from: date, date_to: date) -> Dict:
        tenants = await self.org_client.list_tenants()

        async def fetch_alerts(tenant):
            alerts = await self.alerts_client.list_alerts(
                api_host=tenant["apiHost"],
                tenant_id=tenant["id"],
                date_from=date_from,
                date_to=date_to,
            )
            return tenant["id"], tenant["name"], alerts

        results = await asyncio.gather(
            *[fetch_alerts(t) for t in tenants]
        )

        # print("ALERT FETCH RESULTS:", results)

        alerts_by_tenant = {
            (tenant_id, tenant_name): alerts for tenant_id, tenant_name, alerts in results
        }
        # print("ALERTS BY TENANT:", alerts_by_tenant)

        return AlertTelemetryAggregator.aggregate(alerts_by_tenant)
