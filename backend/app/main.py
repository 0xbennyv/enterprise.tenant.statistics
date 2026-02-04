# app/main.py

import asyncio
from contextlib import asynccontextmanager
import contextlib
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import sys

from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import setup_logging

from app.routers import tenants, telemetry, exports
from app.workers.reconcile_jobs import reconcile_jobs

# Initialize logging
setup_logging()
logger = logging.getLogger("app")

RECONCILE_INTERVAL = 3600 # run every hour

@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()

    # Periodic background task
    async def periodic_reconcile():
        while not stop_event.is_set():
            try:
                await reconcile_jobs()
            except Exception as e:
                logger.exception("Error in periodic reconciliation", e)
            await asyncio.wait_for(
                stop_event.wait(), timeout=RECONCILE_INTERVAL
            )

    # Start the background task
    task = asyncio.create_task(periodic_reconcile())

    # Run initial reconciliation immediately
    await reconcile_jobs()

    yield  # FastAPI runs app here

    # Shutdown: stop background task
    stop_event.set()
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    print("App shutting down, periodic reconcile stopped")

app = FastAPI(title="Telemetry Collector", lifespan=lifespan)
app.description = "Backend service for collecting telemetry data."

# CORS middleware to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://localhost:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3000",
    ],
    # allow_credentials=True,
    # allow_methods=["*"],
    # allow_headers=["*"],
)

# Middleware to log API calls
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # ms

    client = request.client.host if request.client else "unknown"

    logger.info(
        f"{client} - {request.method} {request.url.path} "
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
app.include_router(exports.router, prefix="/exports", tags=["exports"])