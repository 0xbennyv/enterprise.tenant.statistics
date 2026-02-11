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
    Reconcile one job safely.
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

    # --------------------------------------------------
    # Reset stale running jobs on restart
    # --------------------------------------------------
    if job.status == "running" and rq_status == "missing":
        logger.warning(
            "Job %s was marked running in DB but missing in RQ → resetting to queued and re-enqueueing",
            job.job_id,
        )
        job.status = "queued"
        job.error = None
        await db.commit()
        # continue with reconciliation logic
        telemetry_queue.enqueue(
            run_export_sync,
            job.date_from.isoformat(),
            job.date_to.isoformat(),
            job.tenant_id,
            job_timeout=7200,
            job_id=job.job_id,
        )
        return

    # --------------------------------------------------
    # CASE 1: Job missing in RQ
    # --------------------------------------------------
    if rq_status == "missing":

        if job.status in ["queued", "failed"]:
            logger.warning("Re-enqueueing missing job %s", job.job_id)

            telemetry_queue.enqueue(
                run_export_sync,
                job.date_from.isoformat(),
                job.date_to.isoformat(),
                job.tenant_id,
                job_timeout=7200,
                job_id=job.job_id,
            )

        elif job.status == "running":
            # Worker likely died mid-execution
            logger.warning(
                "Job %s was running but missing in RQ → marking failed",
                job.job_id,
            )
            job.status = "failed"
            job.error = "Worker crashed or Redis restarted"
            await db.commit()

        return

    # --------------------------------------------------
    # CASE 2: RQ says failed
    # --------------------------------------------------
    if rq_status == "failed":

        if job.status in ["queued", "running", "failed"]:
            logger.warning(
                "RQ failed but DB says %s → requeueing %s",
                job.status,
                job.job_id,
            )

            failed_registry = FailedJobRegistry(queue=telemetry_queue)

            try:
                failed_registry.requeue(rq_job, at_front=True)
                job.status = "queued"
                job.error = None
                await db.commit()
            except InvalidJobOperation:
                logger.warning(
                    "Race condition while requeueing %s",
                    job.job_id,
                )

        return

    # --------------------------------------------------
    # CASE 3: RQ says started
    # --------------------------------------------------
    if rq_status == "started":

        if job.status != "running":
            logger.info(
                "Updating DB → running for job %s",
                job.job_id,
            )
            job.status = "running"
            await db.commit()

        return

    # --------------------------------------------------
    # CASE 4: RQ says finished
    # --------------------------------------------------
    if rq_status == "finished":

        if job.status != "completed":
            logger.info(
                "Updating DB → completed for job %s",
                job.job_id,
            )
            job.status = "completed"
            job.error = None
            await db.commit()

        return

    # --------------------------------------------------
    # CASE 5: RQ says queued
    # --------------------------------------------------
    if rq_status == "queued":

        if job.status != "queued":
            logger.info(
                "Updating DB → queued for job %s",
                job.job_id,
            )
            job.status = "queued"
            await db.commit()

        return
