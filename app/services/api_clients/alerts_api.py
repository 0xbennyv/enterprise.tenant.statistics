# app/services/api_clients/alerts_api.py

from typing import List, Dict, Any
from datetime import date
from app.services.api_clients.base import BaseApiClient

class AlertsApiClient(BaseApiClient):
    async def list_alerts(
        self,
        api_host: str,
        tenant_id: str,
        date_from: date,
        date_to: date
    ) -> List[Dict[str, Any]]:
        """
        Fetch all alerts for a tenant within a time range.
        Handles pagination automatically.
        """
        alerts = []
        page = 1

        while True:
            url = f"{api_host}/common/v1/alerts"
            headers = {"X-Tenant-ID": tenant_id}
            params = {
                "from": date_from.isoformat(),
                "to": date_to.isoformat(),
                "sort": "raisedat:asc",
                "page": page,
                "pageTotal": "true",
            }
            print("tenant_id:", tenant_id, "host:", api_host)
            resp = await self.get(url, headers=headers, params=params)
            alerts.extend(resp.get("items", []))
            print("fetched", len(resp.get("items", [])), "alerts for tenant", tenant_id, "page", page)
            pages = resp.get("pages", {})
            if page >= pages.get("total", 1):
                break

            page += 1

        return alerts
