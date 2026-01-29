# app/services/api_clients/org_api.py

from typing import List, Dict, Any
from app.services.api_clients.base import BaseApiClient
from app.services.token_manager import TokenManager

class OrgApiClient(BaseApiClient):
    """
    Org API client that leverages TokenManager cached org info.
    """

    def __init__(self, token_manager: TokenManager):
        super().__init__(token_manager)

    async def get_organization_id(self) -> str:
        """
        Returns the organization ID from cached whoami info.
        """
        org_info = await self.token_manager.get_org_info()
        return org_info["id"]

    async def list_tenants(self) -> List[Dict[str, Any]]:
        """
        List all tenants for the organization.
        """
        org_info = await self.token_manager.get_org_info()
        org_id = org_info["id"]
        global_url = org_info["apiHosts"]["global"]

        tenants = []
        page = 1
        while True:
            url = f"{global_url}/organization/v1/tenants"
            headers = {"X-Organization-ID": org_id}
            params = {"page": page, "pageTotal": "true"}
            resp = await self.get(url, headers=headers, params=params)

            tenants.extend(resp.get("items", []))

            # Pagination
            pages_total = resp.get("pages", {}).get("total", 1)
            if page >= pages_total:
                break

            # FOR TESTING, LIMIT TO FIRST PAGE ONLY
            page += 1
            # page = pages_total  # Fetch only first page

        return tenants
