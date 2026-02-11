# app/workers/reconcile_jobs.py

import logging
from sqlalchemy import select
from rq.job import Job
from rq.exceptions import NoSuchJobError, InvalidJobOperation
from rq.registry import FailedJobRegistry, StartedJobRegistry, FinishedJobRegistry

from app.core.database import get_worker_db
from app.models import ExportJob
from app.services.redis_queue import telemetry_queue
from app.workers.telemetry_export_sync import run_export_sync

logger = logging.getLogger("app.reconcile")


async def reconcile_jobs():
    """
    Production-grade reconciliation between Postgres and RQ.

    Rules:
    - DB is authoritative
    - RQ state is repaired to match DB state
    - No exception should crash reconciliation
    """

    redis_conn = telemetry_queue.connection

    async with get_worker_db() as db:
        result = await db.execute(
            select(ExportJob).where(
                ExportJob.status.in_(["queued", "failed", "running"])
            )
        )
        jobs = result.scalars().all()

        for job in jobs:
            try:
                await _reconcile_single_job(job, db, redis_conn)
            except Exception:
                logger.exception(
                    "Reconciliation failed for job %s",
                    job.job_id,
                )
                # DO NOT re-raise — reconciliation must continue
                continue


async def _reconcile_single_job(job, db, redis_conn):
    """
    Deterministic, resurrection-safe reconciliation.
    DB is authoritative.
    """

    try:
        rq_job = Job.fetch(job.job_id, connection=redis_conn)
        rq_status = rq_job.get_status()
    except NoSuchJobError:
        rq_job = None
        rq_status = "missing"

    logger.info(
        "Reconciling job %s | DB=%s | RQ=%s",
        job.job_id,
        job.status,
        rq_status,
    )

    # ==========================================================
    # HARD TERMINAL GUARD
    # ==========================================================
    if job.status in ["cancelled", "completed"]:
        logger.info(
            "Skipping terminal job %s (%s)",
            job.job_id,
            job.status,
        )
        return

    # ==========================================================
    # CRASH RECOVERY: Docker killed while running
    # ==========================================================
    if job.status == "running" and rq_status == "missing":
        logger.warning(
            "Job %s was running but missing in RQ. Requeueing (crash recovery)",
            job.job_id,
        )

        job.status = "queued"
        job.error = None
        await db.commit()

        telemetry_queue.enqueue(
            run_export_sync,
            job.date_from.isoformat(),
            job.date_to.isoformat(),
            job.tenant_id,
            job_timeout=7200,
            job_id=job.job_id,
        )
        return

    # ==========================================================
    # QUEUED but missing in Redis. Redis restart recovery
    # ==========================================================
    if job.status == "queued" and rq_status == "missing":
        logger.warning(
            "Queued job %s missing in Redis. Requeueing",
            job.job_id,
        )

        telemetry_queue.enqueue(
            run_export_sync,
            job.date_from.isoformat(),
            job.date_to.isoformat(),
            job.tenant_id,
            job_timeout=7200,
            job_id=job.job_id,
        )
        return

    # ==========================================================
    # RQ FAILED
    # ==========================================================
    if rq_status == "failed":

        # Only retry if DB explicitly says failed
        if job.status == "failed":
            logger.warning(
                "Retrying explicitly failed job %s",
                job.job_id,
            )

            failed_registry = FailedJobRegistry(queue=telemetry_queue)

            try:
                failed_registry.requeue(rq_job, at_front=True)
                job.status = "queued"
                job.error = None
                await db.commit()
            except InvalidJobOperation:
                logger.warning("Race while requeueing %s", job.job_id)

        else:
            logger.info(
                "RQ failed but DB=%s. not requeueing %s",
                job.status,
                job.job_id,
            )

        return

    # ==========================================================
    # RQ STARTED
    # ==========================================================
    if rq_status == "started":

        # Only allow transition to running from queued
        if job.status == "queued":
            logger.info(
                "Updating DB. running for job %s",
                job.job_id,
            )
            job.status = "running"
            await db.commit()

        return

    # ==========================================================
    # RQ FINISHED
    # ==========================================================
    if rq_status == "finished":

        # Only auto-complete if DB was running
        if job.status == "running":
            logger.info(
                "Updating DB. completed for job %s",
                job.job_id,
            )
            job.status = "completed"
            job.error = None
            await db.commit()

        return

    # ==========================================================
    # RQ QUEUED
    # ==========================================================
    if rq_status == "queued":

        if job.status == "running":
            # Worker restarted mid-transition
            logger.info(
                "Correcting DB running. queued for job %s",
                job.job_id,
            )
            job.status = "queued"
            await db.commit()

        return
