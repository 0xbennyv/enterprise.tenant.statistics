# app/services/api_clients/base.py

import logging
import time
import httpx
from typing import Dict, Any
from app.services.token_manager import TokenManager
from app.services.api_clients.exceptions import ApiClientError
from app.core.http_client import create_async_http_client
from app.core.retry import with_retries

logger = logging.getLogger("app.api_client")

class BaseApiClient:
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self.client = create_async_http_client()

    @with_retries()
    async def get(self, url: str, headers: Dict[str, str] = None, params: Dict[str, Any] = None):
        access_token = await self.token_manager.get_token()
        headers = headers or {}
        headers["Authorization"] = f"Bearer {access_token}"

        start_time = time.time()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers, params=params)
        duration = (time.time() - start_time) * 1000
        logger.info(f"GET {url} status={response.status_code} duration={duration:.2f}ms")

        if response.status_code == 404:
            logger.info("Resource not found: %s", url)
            return {"_error": "not_found"}

        if response.status_code >= 500:
            logger.warning(
                "Server error %s calling %s",
                response.status_code,
                url,
            )
            return {"_error": "server_error"}

        response.raise_for_status()
        return response.json()

    @with_retries()
    async def post(self, url: str, headers: Dict[str, str] = None, json: Dict[str, Any] = None):
        access_token = await self.token_manager.get_token()
        headers = headers or {}
        headers["Authorization"] = f"Bearer {access_token}"

        start_time = time.time()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=headers, json=json)
        duration = (time.time() - start_time) * 1000
        logger.info(f"POST {url} status={response.status_code} duration={duration:.2f}ms")
        response.raise_for_status()
        return response.json()
