# # app/workers/telemetry_export_sync.py
# import asyncio
# from app.workers.telemetry_export import run_export

# def run_export_sync(job_id: str, date_from: str, date_to: str):
#     """
#     Sync wrapper for RQ to run async export job.
#     Use this in RQ queue.enqueue.
#     """
#     try:
#         asyncio.run(run_export(job_id, date_from, date_to))
#     except Exception as e:
#         # Optionally log to file or stdout
#         import traceback, logging
#         logging.exception(f"Export job {job_id} failed: {e}")
#         print(traceback.format_exc())
#         raise

# async def _run(job_id: str, date_from: str, date_to: str):
#     from app.workers.telemetry_export import run_export
#     await run_export(job_id, date_from, date_to)

# app/workers/telemetry_export_sync.py
import asyncio
import logging

from app.workers.telemetry_export import run_export


def run_export_sync(job_id: str, date_from: str, date_to: str):
    """
    Sync wrapper for RQ to run async export job.
    """

    # Windows + asyncpg stability
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(
            asyncio.WindowsSelectorEventLoopPolicy()
        )

    try:
        asyncio.run(run_export(job_id, date_from, date_to))
    except Exception:
        logging.exception(f"Export job {job_id} failed")
        raise
