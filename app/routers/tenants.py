# app/routers/tenants.py

from typing import Any, Dict, Dict
from fastapi import APIRouter
from app.services.token_manager import TokenManager
from app.services.api_clients.org_api import OrgApiClient
from app.core.constants import oauth_url, global_url

router = APIRouter()

token_manager = TokenManager(oauth_url, global_url)
org_client = OrgApiClient(token_manager)

@router.get("/")
async def get_tenants() -> Dict[str, Any]:
    """
    Returns all tenants for the organization.
    Uses cached org info from TokenManager.
    """
    org_id = await org_client.get_organization_id()
    tenants = await org_client.list_tenants()
    return {"organization_id": org_id, "tenants": tenants}