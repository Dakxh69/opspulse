"""
OpsPulse Backend — Tests: Alert Rule Management (Day 12)
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
async def users_fixture(
    db_session: AsyncSession,
) -> tuple[AsyncClient, AsyncClient]:
    """Provides logged-in Operator client and Viewer client."""
    op_email = f"operator_{uuid.uuid4().hex[:8]}@opspulse.local"
    vi_email = f"viewer_{uuid.uuid4().hex[:8]}@opspulse.local"

    operator = User(
        email=op_email,
        password_hash=hash_secret("Password123!"),
        role=UserRole.OPERATOR,
        is_active=True,
    )
    viewer = User(
        email=vi_email,
        password_hash=hash_secret("Password123!"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add_all([operator, viewer])
    await db_session.commit()

    op_client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    await op_client.post("/api/v1/auth/login", json={"email": op_email, "password": "Password123!"})

    vi_client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    await vi_client.post("/api/v1/auth/login", json={"email": vi_email, "password": "Password123!"})

    return op_client, vi_client


@pytest.mark.asyncio
async def test_alert_rule_rbac(
    users_fixture: tuple[AsyncClient, AsyncClient],
) -> None:
    """Verifies that Viewers cannot create rules (403), while Operators can (201)."""
    op_client, vi_client = users_fixture

    rule_payload = {
        "name": "High CPU Warning",
        "metric_key": "cpu.usage_percent",
        "operator": ">",
        "threshold": 80.0,
        "severity": "WARNING",
        "evaluation_window_seconds": 60,
        "consecutive_breaches": 2,
        "cooldown_seconds": 300,
    }

    # 1. Viewer attempt -> 403 Forbidden
    res_vi = await vi_client.post("/api/v1/alerts/rules", json=rule_payload)
    assert res_vi.status_code == 403

    # 2. Operator attempt -> 201 Created
    res_op = await op_client.post("/api/v1/alerts/rules", json=rule_payload)
    assert res_op.status_code == 201
    data = res_op.json()
    assert data["name"] == "High CPU Warning"
    assert data["threshold"] == 80.0
    assert data["severity"] == "WARNING"


@pytest.mark.asyncio
async def test_alert_rule_crud_and_audit(
    users_fixture: tuple[AsyncClient, AsyncClient],
    db_session: AsyncSession,
) -> None:
    """Tests full CRUD lifecycle and audit logging for alert rules."""
    op_client, vi_client = users_fixture

    # 1. Create rule
    res_create = await op_client.post(
        "/api/v1/alerts/rules",
        json={
            "name": "Disk Critical Alert",
            "metric_key": "disk.usage_percent",
            "operator": ">=",
            "threshold": 90.0,
            "severity": "CRITICAL",
            "evaluation_window_seconds": 120,
            "consecutive_breaches": 3,
            "cooldown_seconds": 600,
            "dimension_filter": "/",
        },
    )
    assert res_create.status_code == 201
    rule_id = res_create.json()["id"]

    # 2. List rules (Viewer can read)
    res_list = await vi_client.get("/api/v1/alerts/rules")
    assert res_list.status_code == 200
    rules = res_list.json()
    assert any(r["id"] == rule_id for r in rules)

    # 3. Retrieve rule details
    res_get = await vi_client.get(f"/api/v1/alerts/rules/{rule_id}")
    assert res_get.status_code == 200
    assert res_get.json()["metric_key"] == "disk.usage_percent"

    # 4. Update rule (Operator modifies threshold)
    res_patch = await op_client.patch(
        f"/api/v1/alerts/rules/{rule_id}",
        json={"threshold": 92.5, "cooldown_seconds": 900},
    )
    assert res_patch.status_code == 200
    updated = res_patch.json()
    assert updated["threshold"] == 92.5
    assert updated["cooldown_seconds"] == 900

    # 5. Delete rule
    res_del = await op_client.delete(f"/api/v1/alerts/rules/{rule_id}")
    assert res_del.status_code == 200

    # 6. Verify 404 after deletion
    res_deleted = await vi_client.get(f"/api/v1/alerts/rules/{rule_id}")
    assert res_deleted.status_code == 404

    # 7. Verify audit trail entries
    audit_stmt = select(AuditLog).where(
        AuditLog.target_type == "alert_rule",
        AuditLog.target_id == str(rule_id),
    )
    logs = (await db_session.execute(audit_stmt)).scalars().all()
    actions = {log.action for log in logs}
    assert "ALERT_RULE_CREATED" in actions
    assert "ALERT_RULE_UPDATED" in actions
    assert "ALERT_RULE_DELETED" in actions

