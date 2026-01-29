# app/core/database.py
# from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
# from sqlalchemy.orm import sessionmaker
# from app.core.config import settings
# from typing import AsyncGenerator

# DATABASE_URL = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True, future=True)
# AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# # -----------------------------
# # FastAPI dependency
# # -----------------------------
# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     """
#     Async dependency for FastAPI routes
#     """
#     async with AsyncSessionLocal() as session:
#         yield session


# # -----------------------------
# # Worker-friendly async context manager
# # -----------------------------
# from contextlib import asynccontextmanager

# @asynccontextmanager
# async def get_worker_db() -> AsyncGenerator[AsyncSession, None]:
#     """
#     Async context manager for worker tasks.
#     Use like:
#         async with get_worker_db() as db:
#             ...
#     """
#     session: AsyncSession = AsyncSessionLocal()
#     try:
#         yield session
#     finally:
#         await session.close()


# Dependency
# async def get_db():
#     async with AsyncSessionLocal() as session:
#         yield session


# app/core/database.py
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

DATABASE_URL = (
    f"postgresql+asyncpg://{settings.DB_USER}:"
    f"{settings.DB_PASSWORD}@{settings.DB_HOST}:"
    f"{settings.DB_PORT}/{settings.DB_NAME}"
)


# ---------------------------------
# Engine / Session factory (CRITICAL)
# ---------------------------------
def create_engine_and_session() -> tuple[AsyncEngine, sessionmaker]:
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,               # turn on only when debugging
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    SessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return engine, SessionLocal

# -----------------------------
# FastAPI dependency
# -----------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    engine, SessionLocal = create_engine_and_session()

    async with SessionLocal() as session:
        yield session


# -----------------------------
# Worker-friendly async context
# -----------------------------
@asynccontextmanager
async def get_worker_db() -> AsyncGenerator[AsyncSession, None]:
    engine, SessionLocal = create_engine_and_session()

    async with SessionLocal() as session:
        yield session
