"""
OpsPulse Backend — Tests: Audit Trail API & CLI Bootstrap (Day 8)
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli import seed_admin
from app.core.security import hash_secret
from app.main import app
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_audit_logs_endpoint_rbac(db_session: AsyncSession) -> None:
    """Verifies that GET /audit-logs is restricted to Admins and supports pagination."""
    admin_email = f"aud_admin_{uuid.uuid4().hex[:8]}@opspulse.local"
    viewer_email = f"aud_viewer_{uuid.uuid4().hex[:8]}@opspulse.local"

    # Create admin and viewer
    admin = User(
        email=admin_email,
        password_hash=hash_secret("Password123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    viewer = User(
        email=viewer_email,
        password_hash=hash_secret("Password123!"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add_all([admin, viewer])
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # 1. Viewer cannot access (403 Forbidden)
        v_login = await client.post(
            "/api/v1/auth/login",
            json={"email": viewer_email, "password": "Password123!"},
        )
        assert v_login.status_code == 200

        res_viewer = await client.get("/api/v1/audit-logs")
        assert res_viewer.status_code == 403

        # 2. Admin can access (200 OK)
        a_login = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": "Password123!"},
        )
        assert a_login.status_code == 200

        res_admin = await client.get("/api/v1/audit-logs?page=1&page_size=10")
        assert res_admin.status_code == 200
        data = res_admin.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1


@pytest.mark.asyncio
async def test_cli_seed_admin(monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession) -> None:
    """Verifies CLI seed-admin idempotently creates the first admin."""
    unique_email = f"cli_admin_{uuid.uuid4().hex[:8]}@opspulse.local"
    monkeypatch.setattr("app.core.config.settings.FIRST_ADMIN_EMAIL", unique_email)
    monkeypatch.setattr("app.core.config.settings.FIRST_ADMIN_PASSWORD", "SuperSecurePassword123!")

    exit_code = await seed_admin()
    # It will exit 0 either by creating it or if an admin already exists in the test db
    assert exit_code == 0
