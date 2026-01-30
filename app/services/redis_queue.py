# app/services/redis_queue.py
import os
import redis
import logging
from rq import Queue
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry
from rq.job import Job

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    # decode_responses=True,
    db=0
)

telemetry_queue = Queue(
    "telemetry",
    connection=redis_client,
    default_timeout=7200,  # 2 hours
)

started = StartedJobRegistry(queue=telemetry_queue)
finished = FinishedJobRegistry(queue=telemetry_queue)
failed = FailedJobRegistry(queue=telemetry_queue)

# ================================
# Job recovery helpers (SAFE)
# ================================

def requeue_started_jobs() -> int:
    """
    Requeue jobs that were marked as 'started' but whose worker died.
    Safe to call repeatedly.
    """
    count = 0

    for job_id in started.get_job_ids():
        job = telemetry_queue.fetch_job(job_id)
        if not job:
            continue

        # Only requeue if job is not actually running
        if job.get_status() == "started":
            logger.warning("Requeueing stuck started job %s", job.id)
            job.requeue()
            count += 1

    return count


def requeue_failed_jobs() -> int:
    """
    Requeue failed jobs explicitly.
    """
    count = 0

    for job_id in failed.get_job_ids():
        job = telemetry_queue.fetch_job(job_id)
        if not job:
            continue

        logger.warning("Requeueing failed job %s", job.id)
        job.requeue()
        count += 1

    return count


def reconcile_queue() -> dict:
    """
    Reconcile telemetry queue state.
    Intended to be called from startup and periodically.
    """
    started = requeue_started_jobs()
    failed = requeue_failed_jobs()

    summary = {
        "requeued_started": started,
        "requeued_failed": failed,
    }

    logger.info("Queue reconciliation result: %s", summary)
    return summary

def serialize_job(job):
    return {
        "job_id": job.id,
        "status": job.get_status(),
        "enqueued_at": job.enqueued_at,
        "started_at": job.started_at,
        "ended_at": job.ended_at,
    }