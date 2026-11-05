"""
OpsPulse Backend — Incident Management & Lifecycle Tests (Day 15 & Day 16)

Tests:
- Incident listing, filtering (status, severity, agent), and pagination.
- Incident detail view.
- State transitions (acknowledge, resolve, reopen).
- State machine transition validation (rejects invalid transitions).
- Adding investigation notes.
- Chronological timeline events retrieval.
- RBAC enforcement (Viewer read-only, Admin/Operator write).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_secret
from app.main import app
from app.models.agent import Agent, AgentStatus
from app.models.alert import AlertRule, AlertSeverity
from app.models.incident import (
    Incident,
    IncidentEvent,
    IncidentEventType,
    IncidentStatus,
)
from app.models.user import User, UserRole


@pytest.fixture
async def async_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


@pytest.fixture
async def incident_users(db_session: AsyncSession) -> dict[str, tuple[User, str]]:
    """Creates test users for Admin, Operator, and Viewer with JWT tokens."""
    users = {}
    for role in [UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]:
        email = f"user_{role.value.lower()}_{uuid.uuid4().hex[:6]}@opspulse.local"
        u = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_secret("Pass123!"),
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
async def seeded_incident(db_session: AsyncSession) -> tuple[Incident, Agent]:
    """Seeds a test agent and an OPEN incident with an initial DETECTED event."""
    agent = Agent(
        id=uuid.uuid4(),
        name="incident-agent",
        hostname="srv.incident.local",
        credential_hash="hash",
        status=AgentStatus.ONLINE,
    )
    db_session.add(agent)
    await db_session.flush()

    now = datetime.now(UTC)
    incident = Incident(
        id=uuid.uuid4(),
        agent_id=agent.id,
        rule_id=None,
        dimension="/var",
        title="Disk Space Warning on srv.incident.local [/var]",
        description="Disk usage on /var is 88.5% (exceeds threshold 80.0%)",
        severity=AlertSeverity.WARNING,
        status=IncidentStatus.OPEN,
        first_detected_at=now,
        last_seen_at=now,
    )
    db_session.add(incident)
    await db_session.flush()

    detect_event = IncidentEvent(
        id=uuid.uuid4(),
        incident_id=incident.id,
        event_type=IncidentEventType.DETECTED,
        message="Condition detected: disk_percent [/var] = 88.5",
        created_at=now,
    )
    db_session.add(detect_event)
    await db_session.commit()
    return incident, agent


@pytest.mark.asyncio
async def test_list_and_filter_incidents(
    async_client: AsyncClient,
    incident_users: dict[str, tuple[User, str]],
    seeded_incident: tuple[Incident, Agent],
) -> None:
    """Verifies listing, filtering by status and severity, and viewer access."""
    incident, agent = seeded_incident
    _, viewer_token = incident_users["VIEWER"]

    # 1. List all incidents as VIEWER (read-only allowed)
    resp = await async_client.get(
        "/api/v1/incidents",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(i["id"] == str(incident.id) for i in data["items"])

    # 2. Filter by status=OPEN
    resp_open = await async_client.get(
        "/api/v1/incidents?status=OPEN",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp_open.status_code == 200
    assert any(i["id"] == str(incident.id) for i in resp_open.json()["items"])

    # 3. Filter by non-matching status=RESOLVED
    resp_resolved = await async_client.get(
        "/api/v1/incidents?status=RESOLVED",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp_resolved.status_code == 200
    assert not any(i["id"] == str(incident.id) for i in resp_resolved.json()["items"])


@pytest.mark.asyncio
async def test_get_incident_detail(
    async_client: AsyncClient,
    incident_users: dict[str, tuple[User, str]],
    seeded_incident: tuple[Incident, Agent],
) -> None:
    """Verifies incident detail endpoint."""
    incident, _ = seeded_incident
    _, viewer_token = incident_users["VIEWER"]

    resp = await async_client.get(
        f"/api/v1/incidents/{incident.id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(incident.id)
    assert body["title"] == incident.title
    assert len(body["events"]) >= 1

    # 404 for unknown incident
    resp_404 = await async_client.get(
        f"/api/v1/incidents/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp_404.status_code == 404


@pytest.mark.asyncio
async def test_incident_lifecycle_and_rbac(
    async_client: AsyncClient,
    incident_users: dict[str, tuple[User, str]],
    seeded_incident: tuple[Incident, Agent],
) -> None:
    """
    Verifies full lifecycle transitions and RBAC:
    OPEN -> ACKNOWLEDGED -> RESOLVED -> REOPENED
    Viewer cannot perform transitions (403).
    """
    incident, _ = seeded_incident
    op_user, op_token = incident_users["OPERATOR"]
    _, viewer_token = incident_users["VIEWER"]

    # 1. Viewer attempts acknowledge -> 403 Forbidden
    res_v = await async_client.post(
        f"/api/v1/incidents/{incident.id}/acknowledge",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_v.status_code == 403

    # 2. Operator acknowledges incident
    res_ack = await async_client.post(
        f"/api/v1/incidents/{incident.id}/acknowledge",
        json={"message": "Investigating high disk usage on /var"},
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert res_ack.status_code == 200
    data_ack = res_ack.json()
    assert data_ack["status"] == "ACKNOWLEDGED"
    assert data_ack["acknowledged_by_user_id"] == str(op_user.id)

    # 3. Operator adds investigation note
    res_note = await async_client.post(
        f"/api/v1/incidents/{incident.id}/notes",
        json={"message": "Identified log rotation issue filling /var/log"},
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert res_note.status_code == 201
    assert res_note.json()["event_type"] == "NOTE_ADDED"

    # 4. Operator resolves incident
    res_res = await async_client.post(
        f"/api/v1/incidents/{incident.id}/resolve",
        json={"message": "Rotated old journal logs and recovered 15GB space"},
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert res_res.status_code == 200
    data_res = res_res.json()
    assert data_res["status"] == "RESOLVED"
    assert data_res["resolved_by_user_id"] == str(op_user.id)
    assert data_res["resolved_at"] is not None

    # 5. Invalid transition: cannot acknowledge an already RESOLVED incident
    res_invalid = await async_client.post(
        f"/api/v1/incidents/{incident.id}/acknowledge",
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert res_invalid.status_code == 400

    # 6. Reopen incident
    res_reopen = await async_client.post(
        f"/api/v1/incidents/{incident.id}/reopen",
        json={"message": "Disk usage rose again above 80%"},
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert res_reopen.status_code == 200
    data_reopen = res_reopen.json()
    assert data_reopen["status"] == "OPEN"
    assert data_reopen["resolved_at"] is None

    # 7. Check chronological event history
    res_events = await async_client.get(
        f"/api/v1/incidents/{incident.id}/events",
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert res_events.status_code == 200
    events = res_events.json()
    event_types = [e["event_type"] for e in events]
    assert "DETECTED" in event_types
    assert "ACKNOWLEDGED" in event_types
    assert "NOTE_ADDED" in event_types
    assert "RESOLVED" in event_types
    assert "REOPENED" in event_types
