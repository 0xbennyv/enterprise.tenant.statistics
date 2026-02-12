# app/services/export_job_service.py

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.export_job import ExportJob

ALLOWED_TRANSITIONS = {
    "queued": ["running", "cancelled", "failed"],
    "running": ["queued", "completed", "failed", "cancelling"],
    "cancelling": ["cancelled"],
    "completed": [],
    "failed": ["queued", "running"],
    "cancelled": ["queued"],
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
    if not db.in_transaction():
        async with db.begin():
            job = await _update_job_status_inner(db, job_id, new_status, progress, error, file_path)
    else:
        job = await _update_job_status_inner(db, job_id, new_status, progress, error, file_path)

    return job

async def _update_job_status_inner(
    db: AsyncSession,
    job_id: str,
    new_status: str,
    progress: dict | None,
    error: str | None,
    file_path: str | None,
):
    result = await db.execute(select(ExportJob).where(ExportJob.job_id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return None

    if job.status == new_status:
        return job

    if new_status not in ALLOWED_TRANSITIONS[job.status]:
        raise ValueError(f"Invalid status transition: {job.status} to {new_status}")

    job.status = new_status
    if progress is not None:
        job.progress = progress
    if error is not None:
        job.error = error
    if file_path is not None:
        job.file_path = file_path

    # Force flush so the change is persisted immediately
    await db.flush()
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

async def _apply_job_status_update(
    db: AsyncSession,
    job_id: str,
    new_status: str,
    *,
    progress: dict | None = None,
    error: str | None = None,
    file_path: str | None = None,
):
    result = await db.execute(
        select(ExportJob).where(ExportJob.job_id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        return None

    if job.status == new_status:
        return job

    if new_status not in ALLOWED_TRANSITIONS[job.status]:
        raise ValueError(
            f"Invalid status transition: {job.status} to {new_status}"
        )

    job.status = new_status
    if progress is not None:
        job.progress = progress
    if error is not None:
        job.error = error
    if file_path is not None:
        job.file_path = file_path

    return job
