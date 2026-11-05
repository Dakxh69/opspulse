"""
OpsPulse Backend — Application Entry Point

The FastAPI application is created here with:
- Lifespan context manager for startup/shutdown
- API router registration
- CORS middleware
- Structured logging setup
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.workers.celery_app import celery_app  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and graceful shutdown."""
    configure_logging()
    logger.info("OpsPulse backend starting up", extra={"version": settings.APP_VERSION})
    yield
    logger.info("OpsPulse backend shutting down")


def create_application() -> FastAPI:
    """Factory function that creates and configures the FastAPI application."""
    application = FastAPI(
        title="OpsPulse API",
        description=(
            "Distributed Infrastructure Monitoring & Incident Management Platform — "
            "REST API and WebSocket gateway."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # --- CORS ---
    # In production, only allow the specific frontend origin.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,  # required for HttpOnly cookie auth
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers ---
    application.include_router(api_router, prefix="/api/v1")

    return application


app = create_application()
