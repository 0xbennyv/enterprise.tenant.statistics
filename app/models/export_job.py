# app/models/export_job.py
from sqlalchemy import Column, String, DateTime, JSON
from app.core.database_sync import engine
from sqlalchemy.orm import declarative_base
from datetime import datetime

from app.models.base import Base

class ExportJob(Base):
    __tablename__ = "export_jobs"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    progress = Column(JSON, nullable=True)
    file_path = Column(String, nullable=True)
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Base.metadata.create_all(bind=engine)
