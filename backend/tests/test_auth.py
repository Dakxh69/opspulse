"""
OpsPulse Backend — Tests: Authentication & Session Management (Day 8)
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_secret
from app.main import app
from app.models.audit import AuditLog
from app.models.user import User, UserRole


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Fixture providing a unique active Admin user."""
    unique_email = f"admin_{uuid.uuid4().hex[:8]}@opspulse.local"
    user = User(
        email=unique_email,
        password_hash=hash_secret("AdminPassword123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Fixture providing a unique active Viewer user."""
    unique_email = f"viewer_{uuid.uuid4().hex[:8]}@opspulse.local"
    user = User(
        email=unique_email,
        password_hash=hash_secret("ViewerPassword123!"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_login_success_and_sets_cookie(admin_user: User) -> None:
    """Successful login sets HttpOnly access_token cookie and returns user profile."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "AdminPassword123!"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == admin_user.email
    assert data["role"] == "ADMIN"
    assert "access_token" in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_password(admin_user: User, db_session: AsyncSession) -> None:
    """Failed login returns 401 and writes LOGIN_FAILED audit entry."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "WrongPassword!"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

    # Verify audit log
    stmt = (
        select(AuditLog)
        .where(AuditLog.action == "LOGIN_FAILED", AuditLog.target_id == admin_user.email)
        .order_by(AuditLog.created_at.desc())
    )
    res = await db_session.execute(stmt)
    audit = res.scalars().first()
    assert audit is not None


@pytest.mark.asyncio
async def test_auth_me_authenticated_and_unauthenticated(admin_user: User) -> None:
    """GET /auth/me returns 200 with valid session cookie, 401 without."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Unauthenticated
        unauth_resp = await client.get("/api/v1/auth/me")
        assert unauth_resp.status_code == 401

        # Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "AdminPassword123!"},
        )
        assert login_resp.status_code == 200

        # Authenticated using cookie jar
        me_resp = await client.get("/api/v1/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == admin_user.email


@pytest.mark.asyncio
async def test_logout_clears_cookie(admin_user: User) -> None:
    """POST /auth/logout clears session cookie and subsequent calls are unauthenticated."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        await client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "AdminPassword123!"},
        )

        logout_resp = await client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 200

        me_resp = await client.get("/api/v1/auth/me")
        assert me_resp.status_code == 401


@pytest.mark.asyncio
async def test_register_user_admin_only(admin_user: User, viewer_user: User) -> None:
    """Only Admin can create users and assign roles; viewers receive 403."""
    target_email = f"operator_{uuid.uuid4().hex[:8]}@opspulse.local"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # 1. Viewer attempt -> 403
        await client.post(
            "/api/v1/auth/login",
            json={"email": viewer_user.email, "password": "ViewerPassword123!"},
        )
        viewer_reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": target_email,
                "password": "SecurePassword123!",
                "role": "OPERATOR",
            },
        )
        assert viewer_reg.status_code == 403

        # 2. Admin attempt -> 201 Created
        await client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "AdminPassword123!"},
        )
        admin_reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": target_email,
                "password": "SecurePassword123!",
                "role": "OPERATOR",
            },
        )
        assert admin_reg.status_code == 201
        data = admin_reg.json()
        assert data["email"] == target_email
        assert data["role"] == "OPERATOR"
