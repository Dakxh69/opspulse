"""
OpsPulse Backend — Health Check Endpoints

Provides lightweight liveness and readiness probes:
- GET /api/v1/health  — always returns OK if the process is alive
- GET /health         — alias at the root level (also mounted in main.py)

Future work (Day 3+): Add database and Redis connectivity checks to the
readiness probe so Docker and load balancers can detect degraded state.

Why separate health endpoints?
- Load balancers, Docker HEALTHCHECK, and Kubernetes use different paths.
- /health is a common default; /api/v1/health fits within the API namespace.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: Literal["ok", "degraded", "error"]
    version: str
    # Future: add "database": "ok" | "error", "redis": "ok" | "error"


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    """
    Liveness probe.

    Returns HTTP 200 with status='ok' if the application is running.
    Does NOT yet check database or Redis connectivity — that is a Day 3+ task.
    """
    from app.core.config import settings

    logger.debug("Health check requested")
    return HealthResponse(status="ok", version=settings.APP_VERSION)
