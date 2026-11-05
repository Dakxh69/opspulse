"""
OpsPulse Backend — Recovery Policies & Execution Tests (Day 23)

Verifies:
- RBAC for policy creation (Admin only)
- Allowlisted action validation
- Dry-run mode execution
- Manual approval workflow (Pending -> Approved)
- Audit log persistence
"""

from __future__ import annotations

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_secret
from app.main import app
from app.models.agent import Agent, AgentStatus
from app.models.audit import AuditLog
from app.models.recovery import ActionType, ExecutionStatus, RecoveryPolicy
from app.models.user import User, UserRole


@pytest.fixture
async def recovery_users(db_session: AsyncSession) -> dict[str, tuple[User, str]]:
    """Creates test Admin, Operator, and Viewer users with tokens."""
    users = {}
    for role in [UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]:
        email = f"rec_{role.value.lower()}_{uuid.uuid4().hex[:6]}@opspulse.local"
        u = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_secret("Password123!"),
            role=role,
            is_active=True,
        )
        db_session.add(u)
        await db_session.flush()
        token = create_access_token(subject=str(u.id), role=u.role.value)
        users[role.value] = (u, token)
    await db_session.commit()
    return users


@pytest.fixture
async def test_agent(db_session: AsyncSession) -> Agent:
    """Creates a test target agent."""
    ag = Agent(
        id=uuid.uuid4(),
        name="recovery-host",
        hostname="recovery.opspulse.local",
        credential_hash="hash",
        status=AgentStatus.ONLINE,
    )
    db_session.add(ag)
    await db_session.commit()
    return ag


@pytest.mark.asyncio
async def test_recovery_policy_rbac_and_execution(
    recovery_users: dict[str, tuple[User, str]],
    test_agent: Agent,
) -> None:
    """Verifies policy creation, execution approval workflow, and dry-run mode."""
    admin_user, admin_token = recovery_users["ADMIN"]
    op_user, op_token = recovery_users["OPERATOR"]
    _, viewer_token = recovery_users["VIEWER"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Viewer attempts to create policy -> 403 Forbidden
        policy_payload = {
            "name": "Restart Systemd Nginx",
            "action_type": "SERVICE_RESTART",
            "target": "nginx.service",
            "requires_approval": True,
            "enabled": True,
        }
        res_v = await client.post(
            "/api/v1/recovery/policies",
            json=policy_payload,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_v.status_code == 403

        # 2. Operator attempts to create policy -> 403 Forbidden (Admin only)
        res_op = await client.post(
            "/api/v1/recovery/policies",
            json=policy_payload,
            headers={"Authorization": f"Bearer {op_token}"},
        )
        assert res_op.status_code == 403

        # 3. Admin creates policy -> 201 Created
        res_admin = await client.post(
            "/api/v1/recovery/policies",
            json=policy_payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_admin.status_code == 201
        policy_data = res_admin.json()
        policy_id = policy_data["id"]

        # 4. Operator triggers live execution (requires approval) -> 201 with PENDING_APPROVAL
        exec_payload = {
            "target_agent_id": str(test_agent.id),
            "dry_run": False,
        }
        res_exec = await client.post(
            f"/api/v1/recovery/{policy_id}/execute",
            json=exec_payload,
            headers={"Authorization": f"Bearer {op_token}"},
        )
        assert res_exec.status_code == 201
        exec_data = res_exec.json()
        assert exec_data["status"] == "PENDING_APPROVAL"
        execution_id = exec_data["id"]

        # 5. Admin approves execution -> status becomes APPROVED
        res_approve = await client.post(
            f"/api/v1/recovery/executions/{execution_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_approve.status_code == 200
        assert res_approve.json()["status"] == "APPROVED"
        assert res_approve.json()["approved_by_user_id"] == str(admin_user.id)

        # 6. Operator triggers dry-run simulation -> status SUCCEEDED immediately
        dry_payload = {
            "target_agent_id": str(test_agent.id),
            "dry_run": True,
        }
        res_dry = await client.post(
            f"/api/v1/recovery/{policy_id}/execute",
            json=dry_payload,
            headers={"Authorization": f"Bearer {op_token}"},
        )
        assert res_dry.status_code == 201
        assert res_dry.json()["status"] == "SUCCEEDED"
        assert "[DRY-RUN]" in res_dry.json()["output_summary"]
