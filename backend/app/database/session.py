"""
OpsPulse Backend — Database Session & Engine Configuration

Provides:
- Asynchronous SQLAlchemy engine (`create_async_engine`) and sessionmaker
  for non-blocking FastAPI request handling via `asyncpg`.
- FastAPI dependency `get_db()` providing scoped async sessions.
- Synchronous SQLAlchemy engine (`create_engine`) via `psycopg2` for
  Celery tasks and Alembic migrations.
- Liveness/readiness database ping utility (`check_database_health()`).

See DEC-003 for architecture justification.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# =============================================================================
# 1. Asynchronous Database Engine (FastAPI Request Pipeline)
# =============================================================================
# In testing or debug mode, use NullPool to avoid event loop leakage across test runs.
# In production, use AsyncAdaptedQueuePool with pre-ping for high-throughput pooling.
if settings.DEBUG or settings.TESTING:
    async_engine: AsyncEngine = create_async_engine(
        settings.async_database_url,
        poolclass=NullPool,
        echo=settings.DEBUG,
    )
else:
    async_engine = create_async_engine(
        settings.async_database_url,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an isolated asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> bool:
    """Executes a lightweight ping (SELECT 1) to verify database connectivity."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as exc:
        logger.warning("Database health check failed", extra={"error": str(exc)})
        return False


# =============================================================================
# 2. Synchronous Database Engine (Celery Workers & Alembic CLI)
# =============================================================================
sync_engine = create_engine(
    settings.sync_database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
