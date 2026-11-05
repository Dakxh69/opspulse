"""
OpsPulse Backend — Health & Readiness Check Endpoints

Provides liveness and readiness probes:
- GET /api/v1/health  — reports application status, version, and database connectivity.
- GET /health         — alias at the root level.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.database.session import check_database_health

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: Literal["ok", "degraded", "error"]
    version: str
    database: Literal["ok", "error"]


@router.get("/health", response_model=HealthResponse, summary="Health & readiness probe")
async def health_check() -> HealthResponse:
    """
    Liveness and readiness probe.

    Checks:
    1. Application process is running (ok).
    2. PostgreSQL database connection ping (ok or error).
    """
    db_healthy = await check_database_health()

    status: Literal["ok", "degraded", "error"]
    if db_healthy:
        status = "ok"
    else:
        status = "degraded"
        logger.warning("Readiness probe reported degraded state: database is unreachable")

    return HealthResponse(
        status=status,
        version=settings.APP_VERSION,
        database="ok" if db_healthy else "error",
    )
