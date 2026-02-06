# # app/workers/telemetry_export_sync.py

import asyncio
import logging

from app.workers.telemetry_export import run_export
from rq import get_current_job


def run_export_sync(date_from: str, date_to: str, tenant_id: str | None):
    """
    Sync wrapper for RQ to run async export job.
    """

    # Windows + asyncpg stability
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(
            asyncio.WindowsSelectorEventLoopPolicy()
        )

    try:
        job = get_current_job()
    
        asyncio.run(run_export(job.id, date_from, date_to, tenant_id))
    except Exception:
        logging.exception(f"Export job failed")
        raise
