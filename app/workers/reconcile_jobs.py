# app/workers/reconcile_jobs.py

import logging
from app.core.database import get_worker_db
from app.models import ExportJob
from app.services.redis_queue import telemetry_queue, failed
from app.workers.telemetry_export_sync import run_export_sync
from sqlalchemy import select
from rq.job import Job
from rq.exceptions import NoSuchJobError
from rq.registry import FailedJobRegistry

logger = logging.getLogger("app.reconcile")

async def reconcile_jobs():
    """
    Ensure all jobs in Postgres with status='queued' or 'failed' exist in RQ.
    If missing, enqueue them.
    """
    from redis import Redis
    redis_conn = telemetry_queue.connection

    async with get_worker_db() as db:
        result = await db.execute(
            select(ExportJob).where(ExportJob.status.in_(["queued", "failed"]))
        )
        queued_jobs = result.scalars().all()

        for job in queued_jobs:
            try:
                # Check if the job already exists in RQ
                fetched = Job.fetch(job.job_id, connection=redis_conn)
                print(f"Job {job.job_id} already exists in RQ: ", fetched)
                rq_status = fetched.get_status()
                # Job exists and is already executing or queued
                if rq_status in {"queued", "started"}:
                    logger.info(
                        "Job %s already in RQ with status=%s",
                        fetched.id,
                        rq_status,
                    )
                    continue

                # Job exists but failed → requeue explicitly
                if rq_status == "failed":
                    logger.warning("Requeueing failed RQ job %s", fetched.id)
                    fetched.requeue()
                    continue
            except NoSuchJobError:
                # Job missing entirely → enqueue fresh
                logger.warning(
                    "Job %s missing from RQ, re-enqueueing",
                    job.job_id,
                )

                new_job = telemetry_queue.enqueue(
                    run_export_sync,
                    job.date_from.isoformat(),
                    job.date_to.isoformat(),
                    job_timeout=7200,
                    job_id=job.job_id,
                )

                # Ensure DB stays authoritative
                job.job_id = new_job.id
                await db.commit()

            except Exception as e:
                # Real errors should surface
                logger.exception(
                    "Failed to reconcile job %s: %s",
                    job.job_id,
                    e,
                )
                raise