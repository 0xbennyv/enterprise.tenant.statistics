# app/core/http_client.py

import httpx

def create_async_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=10.0,
            read=30.0,
            write=30.0,
            pool=10.0,
        ),
        limits=httpx.Limits(
            max_connections=20,
            max_keepalive_connections=10,
        ),
        headers={
            "User-Agent": "telemetry-exporter/1.0",
        },
    )
