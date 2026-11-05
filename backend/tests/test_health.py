"""
OpsPulse Backend — Tests: Health Endpoint

Tests the GET /api/v1/health endpoint using FastAPI's test client.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_200() -> None:
    """Health endpoint must return HTTP 200."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_returns_ok_or_degraded() -> None:
    """Health endpoint returns ok if DB is up, or degraded if DB is unreachable in test env."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/health")

    data = response.json()
    assert data["status"] in {"ok", "degraded"}


@pytest.mark.asyncio
async def test_health_returns_version() -> None:
    """Health endpoint must return a non-empty version string."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/health")

    data = response.json()
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


@pytest.mark.asyncio
async def test_health_response_schema() -> None:
    """Health endpoint response must conform strictly to expected schema."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/health")

    data = response.json()
    assert set(data.keys()) == {"status", "version", "database"}
    assert data["status"] in {"ok", "degraded", "error"}
    assert data["database"] in {"ok", "error"}
