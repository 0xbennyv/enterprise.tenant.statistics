# app/services/api_clients/health_check_api.py

from typing import Dict, Any
from app.services.api_clients.base import BaseApiClient
from app.services.token_manager import TokenManager


class HealthCheckApiClient(BaseApiClient):
    def __init__(self, token_manager: TokenManager):
        super().__init__(token_manager)

    async def get_endpoint_health(
        self,
        api_host: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        url = f"{api_host}/account-health-check/v1/health-check"

        return await self.get(
            url=url,
            headers={"X-Tenant-ID": tenant_id},
            params={"products": "endpoint"},
        )
