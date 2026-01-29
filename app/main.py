# app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
import time
import logging
import sys

from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import setup_logging

from app.routers import tenants, telemetry
from app.workers.postgres_rq_sync import sync_postgres_to_rq

# Initialize logging
setup_logging()
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup code
    await sync_postgres_to_rq()
    yield
    # shutdown code (optional)
    print("App shutting down")

app = FastAPI(title="Telemetry Collector", lifespan=lifespan)
app.description = "Backend service for collecting telemetry data."

# Middleware to log API calls
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # ms

    logger.info(
        f"{request.client.host} - {request.method} {request.url.path} "
        f"status={response.status_code} duration={process_time:.2f}ms"
    )
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse({"detail": "Internal server error"}, status_code=500)
    

@app.get("/")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok", "env": settings.ENV}

# Include routers
app.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
app.include_router(telemetry.router, prefix="/telemetry", tags=["telemetry"])