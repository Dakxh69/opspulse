"""
OpsPulse Backend — Tests: Agent Management & Authentication (Day 8)
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_secret
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture
async def admin_client(db_session: AsyncSession) -> AsyncClient:
    """Authenticated HTTP client fixture logged in as an Admin."""
    unique_email = f"agentadmin_{uuid.uuid4().hex[:8]}@opspulse.local"
    user = User(
        email=unique_email,
        password_hash=hash_secret("AdminPassword123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "AdminPassword123!"},
    )
    assert login_res.status_code == 200
    return client


@pytest.mark.asyncio
async def test_agent_provisioning_and_rotation_flow(admin_client: AsyncClient) -> None:
    """Tests agent registration, credential issuance, rotation, and revocation."""
    # 1. Register new agent
    reg_res = await admin_client.post(
        "/api/v1/agents/register",
        json={
            "name": "prod-web-01",
            "hostname": "ubuntu-web-node",
            "os_type": "linux",
            "agent_version": "0.1.0",
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    agent_id = reg_data["agent_id"]
    agent_secret = reg_data["agent_secret"]

    assert agent_id is not None
    assert isinstance(agent_secret, str)
    assert len(agent_secret) == 64

    # 2. List agents (should include newly registered agent, without secret)
    list_res = await admin_client.get("/api/v1/agents")
    assert list_res.status_code == 200
    agents_list = list_res.json()
    matching = [a for a in agents_list if a["id"] == agent_id]
    assert len(matching) == 1
    assert "agent_secret" not in matching[0]
    assert "credential_hash" not in matching[0]

    # 3. Rotate credential
    rot_res = await admin_client.post(f"/api/v1/agents/{agent_id}/rotate-credential")
    assert rot_res.status_code == 200
    rot_data = rot_res.json()
    new_secret = rot_data["new_agent_secret"]
    assert new_secret != agent_secret
    assert len(new_secret) == 64

    # 4. Revoke agent
    del_res = await admin_client.delete(f"/api/v1/agents/{agent_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["status"] == "OFFLINE"
    assert del_data["revoked_at"] is not None
