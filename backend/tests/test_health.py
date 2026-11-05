"""
OpsPulse Backend — Tests: Health Endpoint

Tests the GET /api/v1/health endpoint using FastAPI's test client.

Why httpx + AsyncClient?
- FastAPI's recommended async test approach.
- Works with async route handlers without needing a running server.
- pytest-asyncio (asyncio_mode="auto") handles event loop management.
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
async def test_health_returns_ok_status() -> None:
    """Health endpoint must return status='ok'."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/health")

    data = response.json()
    assert data["status"] == "ok"


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
    """Health endpoint response must conform to expected schema."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/health")

    data = response.json()
    # Must have exactly these keys (no extra data leaking)
    assert set(data.keys()) == {"status", "version"}
    assert data["status"] in {"ok", "degraded", "error"}
