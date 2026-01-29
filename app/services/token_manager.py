# app/services/token_manager.py

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("app.token_manager")

class OAuthToken:
    def __init__(self, access_token: str, refresh_token: str, expires_in: int):
        self.access_token = access_token
        self.refresh_token = refresh_token
        # expires_in is seconds
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 10)  # refresh buffer

    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at

class TokenManager:
    """
    Handles OAuth token fetching and refreshing for external APIs.
    """
    _lock = asyncio.Lock()
    _token: Optional[OAuthToken] = None
    _org_info: Optional[dict] = None  # cache for whoami

    def __init__(self, oauth_url: str, global_url: str):
        self.oauth_url = oauth_url
        self.global_url = global_url

    async def get_token(self) -> str:
        """
        Returns a valid access token. Refreshes automatically if expired.
        """
        if self._token is None or self._token.is_expired():
            async with self._lock:
                # double-check inside lock
                if self._token is None or self._token.is_expired():
                    if self._token and self._token.refresh_token:
                        logger.info("Refreshing access token...")
                        self._token = await self._refresh_token(self._token.refresh_token)
                    else:
                        logger.info("Fetching new access token via client credentials...")
                        self._token = await self._fetch_new_token()

                    # Fetch whoami info once after token refresh
                    self._org_info = await self._fetch_org_info()
        return self._token.access_token

    async def _fetch_new_token(self) -> OAuthToken:
        """
        Client Credentials flow
        """
        data = {
            "grant_type": "client_credentials",
            "scope": "token",
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{self.oauth_url}/api/v2/oauth2/token", data=data)
            resp.raise_for_status()
            json_data = resp.json()

        token = OAuthToken(
            access_token=json_data["access_token"],
            refresh_token=json_data.get("refresh_token"),
            expires_in=json_data["expires_in"]
        )
        logger.info(f"Obtained new access token. Expires in {json_data['expires_in']} seconds.")
        return token

    async def _refresh_token(self, refresh_token: str) -> OAuthToken:
        """
        Refresh token flow
        """
        payload = {
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{self.oauth_url}/api/v2/oauth2/token", json=payload)
            resp.raise_for_status()
            json_data = resp.json()

        token = OAuthToken(
            access_token=json_data["access_token"],
            refresh_token=json_data.get("refresh_token"),
            expires_in=json_data["expires_in"]
        )
        logger.info(f"Refreshed access token. Expires in {json_data['expires_in']} seconds.")
        return token

    async def get_org_info(self) -> dict:
        """
        Returns cached org info. Ensures token is valid.
        """
        await self.get_token()
        return self._org_info

    async def _fetch_org_info(self) -> dict:
        access_token = self._token.access_token
        url = f"{self.global_url}/whoami/v1"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()