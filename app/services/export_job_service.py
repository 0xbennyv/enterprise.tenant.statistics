# app/services/export_job_service.py

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.export_job import ExportJob

ALLOWED_TRANSITIONS = {
    "queued": ["running", "cancelled", "failed"],
    "running": ["completed", "failed", "cancelling"],
    "cancelling": ["cancelled"],
    "completed": [],
    "failed": [],
    "cancelled": [],
}


# async def update_job_status(
#     db: AsyncSession,
#     job_id: str,
#     new_status: str,
#     progress: dict = None,
#     error: str = None,
#     file_path: str = None,
# ):
#     """Safely update ExportJob status with allowed transitions."""
#     result = await db.execute(ExportJob.__table__.select().where(ExportJob.id == job_id))
#     job = result.first()
#     if not job:
#         return None

#     current_status = job._mapping["status"]
#     if new_status not in ALLOWED_TRANSITIONS[current_status]:
#         raise ValueError(f"Invalid status transition: {current_status} → {new_status}")

#     update_values = {"status": new_status}
#     if progress:
#         update_values["progress"] = progress
#     if error:
#         update_values["error"] = error
#     if file_path:
#         update_values["file_path"] = file_path

#     await db.execute(ExportJob.__table__.update().where(ExportJob.id == job_id).values(**update_values))
#     await db.commit()
#     return update_values

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
            select(ExportJob).where(ExportJob.id == job_id)
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

# async def update_job_progress_only(db, job_id: str, progress: dict):
#     """Update progress without touching status."""
#     await db.execute(
#         ExportJob.__table__.update()
#         .where(ExportJob.id == job_id)
#         .values(progress=progress)
#     )
#     await db.commit()

async def update_job_progress_only(
    db: AsyncSession,
    job_id: str,
    progress: dict,
):
    async with db.begin():
        await db.execute(
            update(ExportJob)
            .where(ExportJob.id == job_id)
            .values(progress=progress)
        )
