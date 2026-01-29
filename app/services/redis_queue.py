# app/services/redis_queue.py
import os
import redis
from rq import Queue
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry
from rq.job import Job

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

# Requeue stuck jobs (still running when worker stopped)
for job_id in started.get_job_ids():
    job = Job.fetch(job_id, connection=redis_client)
    job.requeue()
    print(f"Requeued started job {job.id}")

# Requeue failed jobs
for job_id in failed.get_job_ids():
    job = Job.fetch(job_id, connection=redis_client)
    job.requeue()
    print(f"Requeued failed job {job.id}")

def serialize_job(job):
    return {
        "job_id": job.id,
        "status": job.get_status(),
        "enqueued_at": job.enqueued_at,
        "started_at": job.started_at,
        "ended_at": job.ended_at,
    }