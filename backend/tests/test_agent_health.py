"""
OpsPulse Backend — Agent Health Monitoring & Availability Tests (Day 17)

Verifies:
- Agent heartbeat status transitions: ONLINE -> DEGRADED (>60s) -> OFFLINE (>120s)
- Automatic creation of deduplicated "Agent Offline" incident on expiration
- Avoidance of duplicate incidents on repeated health check ticks
- Auto-recovery: Agent returns and sends heartbeat -> status becomes ONLINE and
  the active offline incident is auto-resolved.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import hash_secret
from app.database.session import SyncSessionLocal
from app.main import app
from app.models.agent import Agent, AgentStatus
from app.models.incident import (
    Incident,
    IncidentEventType,
    IncidentStatus,
)
from app.workers.tasks import monitor_agent_health


def test_agent_health_state_transitions_and_deduplication() -> None:
    """Verifies degraded/offline transitions and incident deduplication."""
    with SyncSessionLocal() as session:
        now = datetime.now(UTC)

        # 1. Online agent (heartbeat 10s ago)
        ag_online = Agent(
            id=uuid.uuid4(),
            name="agent-fresh",
            hostname="fresh.opspulse.local",
            credential_hash="hash",
            status=AgentStatus.ONLINE,
            last_heartbeat=now - timedelta(seconds=10),
        )

        # 2. Degraded agent (heartbeat 70s ago)
        ag_degraded = Agent(
            id=uuid.uuid4(),
            name="agent-slow",
            hostname="slow.opspulse.local",
            credential_hash="hash",
            status=AgentStatus.ONLINE,
            last_heartbeat=now - timedelta(seconds=70),
        )

        # 3. Offline agent (heartbeat 200s ago)
        ag_offline = Agent(
            id=uuid.uuid4(),
            name="agent-dead",
            hostname="dead.opspulse.local",
            credential_hash="hash",
            status=AgentStatus.ONLINE,
            last_heartbeat=now - timedelta(seconds=200),
        )

        session.add_all([ag_online, ag_degraded, ag_offline])
        session.commit()

        # Run health monitoring task
        res1 = monitor_agent_health()
        assert res1["degraded_count"] >= 1
        assert res1["offline_count"] >= 1

        # Check DB states
        session.expire_all()
        ag1 = session.get(Agent, ag_online.id)
        ag2 = session.get(Agent, ag_degraded.id)
        ag3 = session.get(Agent, ag_offline.id)

        assert ag1.status == AgentStatus.ONLINE
        assert ag2.status == AgentStatus.DEGRADED
        assert ag3.status == AgentStatus.OFFLINE

        # Verify offline incident created for ag3
        inc_stmt = select(Incident).where(
            Incident.agent_id == ag3.id,
            Incident.dimension == "heartbeat",
        )
        incidents = session.execute(inc_stmt).scalars().all()
        assert len(incidents) == 1
        first_incident = incidents[0]
        assert first_incident.status == IncidentStatus.OPEN
        assert "Agent Offline" in first_incident.title

        # Run health monitoring task again: verify deduplication (no 2nd incident created)
        monitor_agent_health()
        session.expire_all()
        incidents_after = session.execute(inc_stmt).scalars().all()
        assert len(incidents_after) == 1


@pytest.mark.asyncio
async def test_agent_auto_recovery_on_heartbeat() -> None:
    """Verifies that an offline agent checking in auto-recovers to ONLINE and resolves incident."""
    raw_secret = "test-agent-secret-42"

    with SyncSessionLocal() as session:
        now = datetime.now(UTC)
        ag = Agent(
            id=uuid.uuid4(),
            name="agent-recovering",
            hostname="recovering.opspulse.local",
            credential_hash=hash_secret(raw_secret),
            status=AgentStatus.OFFLINE,
            last_heartbeat=now - timedelta(seconds=300),
        )
        session.add(ag)
        session.flush()

        # Create active offline incident
        inc = Incident(
            id=uuid.uuid4(),
            agent_id=ag.id,
            dimension="heartbeat",
            title=f"Agent Offline: {ag.hostname}",
            description="Agent has missed heartbeats",
            severity="CRITICAL",
            status=IncidentStatus.OPEN,
            first_detected_at=now - timedelta(seconds=200),
            last_seen_at=now - timedelta(seconds=200),
        )
        session.add(inc)
        session.commit()
        agent_id = ag.id
        incident_id = inc.id

    # Agent pings heartbeat endpoint
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.post(
            "/api/v1/agents/heartbeat",
            headers={
                "X-Agent-ID": str(agent_id),
                "X-Agent-Secret": raw_secret,
            },
        )
        assert resp.status_code == 204

    # Verify agent is back ONLINE and incident is RESOLVED
    with SyncSessionLocal() as session:
        agent_refreshed = session.get(Agent, agent_id)
        assert agent_refreshed.status == AgentStatus.ONLINE

        incident_refreshed = session.get(Incident, incident_id)
        assert incident_refreshed.status == IncidentStatus.RESOLVED
        assert incident_refreshed.resolved_at is not None

        # Verify AUTO_CLEARED event logged
        events = incident_refreshed.events
        assert any(e.event_type == IncidentEventType.AUTO_CLEARED for e in events)

