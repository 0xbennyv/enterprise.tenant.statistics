# app/api/cases_api.py

from typing import List, Dict, Any
from datetime import datetime
from app.api.base import BaseApiClient


class CasesApiClient(BaseApiClient):
    async def list_cases(
        self,
        api_host: str,
        tenant_id: str,
        created_after: datetime,
        created_before: datetime,
        status: str = None,
    ) -> List[Dict[str, Any]]:
        cases = []
        page = 1

        while True:
            url = f"{api_host}/cases/v1/cases"
            headers = {"X-Tenant-ID": tenant_id}
            params = {
                "createdAfter": created_after.isoformat().replace("+00:00", "Z"),
                "createdBefore": created_before.isoformat().replace("+00:00", "Z"),
                "sort": "createdAt:asc",
                "page": page,
                "status": status,
            }

            resp = await self.get(url, headers=headers, params=params)
            # print("Case IDs fetched for tenant", tenant_id, "page", page, "items:", ids := [case["id"] for case in resp.get("items", [])])
            cases.extend(resp.get("items", []))

            pages = resp.get("pages", {})
            # print("Pagination info for tenant", tenant_id, "page: ", pages)
            if page >= pages.get("total", 1):
                break

            page += 1

        return cases
