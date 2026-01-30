# app/services/export_job_service.py

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.export_job import ExportJob

ALLOWED_TRANSITIONS = {
    "queued": ["running", "cancelled", "failed"],
    "running": ["completed", "failed", "cancelling"],
    "cancelling": ["cancelled"],
    "completed": [],
    "failed": ["queued", "running"],
    "cancelled": [],
}

async def update_job_status(
    db: AsyncSession,
    job_id: str,
    new_status: str,
    *,
    progress: dict | None = None,
    error: str | None = None,
    file_path: str | None = None,
):
    async with db.begin():
        result = await db.execute(
            select(ExportJob).where(ExportJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            return None

        if new_status not in ALLOWED_TRANSITIONS[job.status]:
            raise ValueError(
                f"Invalid status transition: {job.status} → {new_status}"
            )

        job.status = new_status

        if progress is not None:
            job.progress = progress
        if error is not None:
            job.error = error
        if file_path is not None:
            job.file_path = file_path

    return job

async def update_job_progress_only(
    db: AsyncSession,
    job_id: str,
    progress: dict,
):
    async with db.begin():
        await db.execute(
            update(ExportJob)
            .where(ExportJob.job_id == job_id)
            .values(progress=progress)
        )
