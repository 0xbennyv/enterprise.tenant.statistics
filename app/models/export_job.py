# app/models/export_job.py
from sqlalchemy import Column, Date, Integer, String, DateTime, JSON
from app.core.database_sync import engine
from sqlalchemy.orm import declarative_base
from datetime import datetime

from app.models.base import Base

class ExportJob(Base):
    __tablename__ = "export_jobs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, unique=True, nullable=False)
    date_from = Column(Date)
    date_to = Column(Date)
    status = Column(String, nullable=False)
    progress = Column(JSON, nullable=True)
    file_path = Column(String, nullable=True)
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Base.metadata.create_all(bind=engine)
