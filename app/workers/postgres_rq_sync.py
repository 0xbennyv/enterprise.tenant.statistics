# app/workers/postgres_rq_sync.py

from app.core.database import get_worker_db
from app.models import ExportJob
from app.services.redis_queue import telemetry_queue
from app.workers.telemetry_export_sync import run_export_sync
from sqlalchemy import select
from rq.job import Job

async def sync_postgres_to_rq():
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
                # Job exists → nothing to do
            except Exception:
                # Job not in RQ → enqueue it
                new_job = telemetry_queue.enqueue(
                    run_export_sync,
                    job.date_from.isoformat(),
                    job.date_to.isoformat(),
                    job_timeout=7200,
                )

                # Update job_id in Postgres in case it changed
                job.job_id = new_job.id
                await db.commit()


                print(f"Re-enqueued job {new_job.id} from Postgres")