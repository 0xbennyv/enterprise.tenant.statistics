# app/core/queue.py
import os
import redis
from rq import Queue
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry

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

def serialize_job(job):
    return {
        "job_id": job.id,
        "status": job.get_status(),
        "enqueued_at": job.enqueued_at,
        "started_at": job.started_at,
        "ended_at": job.ended_at,
    }