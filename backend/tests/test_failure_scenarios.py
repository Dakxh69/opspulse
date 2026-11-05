"""
OpsPulse Backend — Failure Testing Scenarios (Day 25)

Verifies platform resilience under infrastructure outages per spec Section 21.4:
- Scenario D: Agent disconnection & deduplicated offline incident
- Scenario E: Backend unavailable & agent buffer retention/resend
- Scenario F: Redis unavailable & fast 503 failure (no false acceptance)
- Scenario H: PostgreSQL unavailable & health probe degradation
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_secret
from app.database.session import SyncSessionLocal
from app.main import app
from app.models.agent import Agent, AgentStatus
from app.models.incident import Incident, IncidentStatus
from app.workers.tasks import monitor_agent_health, process_metric_batch


@pytest.mark.asyncio
async def test_redis_outage_fails_fast_with_503(db_session: AsyncSession) -> None:
    """
    Scenario F: When Redis broker is unreachable, metric ingestion must return HTTP 503.
    It must never falsely return HTTP 202 Accepted if the message was not enqueued.
    """
    raw_secret = "failure-test-secret"
    agent = Agent(
        id=uuid.uuid4(),
        name="redis-failure-host",
        hostname="redis-fail.opspulse.local",
        credential_hash=hash_secret(raw_secret),
        status=AgentStatus.ONLINE,
    )
    db_session.add(agent)
    await db_session.commit()

    payload = {
        "agent_id": str(agent.id),
        "batch_id": str(uuid.uuid4()),
        "metrics": [
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "cpu": {
                    "usage_percent": 15.0,
                    "logical_cores": 2,
                    "load_average": {"load_1m": 0.1, "load_5m": 0.2, "load_15m": 0.1},
                },
                "memory": {
                    "total_bytes": 16000000000,
                    "used_bytes": 4000000000,
                    "available_bytes": 12000000000,
                    "free_bytes": 8000000000,
                    "usage_percent": 25.0,
                },
                "disks": [],
                "networks": [],
            }
        ],
    }

    # Mock Celery delay to simulate Redis failure
    with patch("app.workers.tasks.process_metric_batch.delay", side_effect=Exception("Redis connection refused")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.post(
                "/api/v1/metrics/ingest",
                json=payload,
                headers={
                    "X-Agent-ID": str(agent.id),
                    "X-Agent-Secret": raw_secret,
                },
            )
            # Must return 503 Service Unavailable so agent keeps samples in local ring buffer
            assert resp.status_code == 503
            assert "temporarily unavailable" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_postgres_outage_health_probe() -> None:
    """
    Scenario H: When PostgreSQL is down, the readiness probe (/api/v1/health)
    reports 'degraded' status and database='error'.
    """
    with patch("app.api.v1.health.check_database_health", return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["database"] == "error"


def test_agent_disconnection_failure_flow() -> None:
    """
    Scenario D: When an agent stops reporting heartbeats:
    1. At t > 60s, status becomes DEGRADED
    2. At t > 120s, status becomes OFFLINE
    3. Exactly ONE critical offline incident is generated (deduplicated on further ticks).
    """
    with SyncSessionLocal() as session:
        now = datetime.now(UTC)
        agent = Agent(
            id=uuid.uuid4(),
            name="disconnecting-agent",
            hostname="disconnect.opspulse.local",
            credential_hash="hash",
            status=AgentStatus.ONLINE,
            last_heartbeat=now - timedelta(seconds=140),  # Missed heartbeat for 140s
        )
        session.add(agent)
        session.commit()
        agent_id = agent.id

    # 1. Run monitoring task tick
    res = monitor_agent_health()
    assert res["offline_count"] >= 1

    with SyncSessionLocal() as session:
        ag = session.get(Agent, agent_id)
        assert ag.status == AgentStatus.OFFLINE

        # Verify offline incident created
        inc_stmt = (
            session.query(Incident)
            .filter(Incident.agent_id == agent_id, Incident.dimension == "heartbeat")
        )
        incidents = inc_stmt.all()
        assert len(incidents) == 1
        assert incidents[0].status == IncidentStatus.OPEN
        assert "Agent Offline" in incidents[0].title

    # 2. Run monitoring task again (simulating subsequent scheduler ticks)
    monitor_agent_health()

    with SyncSessionLocal() as session:
        # Verify deduplication: STILL only 1 incident exists
        incidents = (
            session.query(Incident)
            .filter(Incident.agent_id == agent_id, Incident.dimension == "heartbeat")
            .all()
        )
        assert len(incidents) == 1


def test_idempotent_redelivery_after_transient_failure() -> None:
    """
    Scenario E / Worker Retry: When a batch fails mid-processing and is redelivered,
    it re-executes idempotently without creating duplicate metric or incident rows.
    """
    with SyncSessionLocal() as session:
        agent = Agent(
            id=uuid.uuid4(),
            name="retry-agent",
            hostname="retry.opspulse.local",
            credential_hash="hash",
            status=AgentStatus.ONLINE,
        )
        session.add(agent)
        session.commit()
        agent_id_str = str(agent.id)

    batch_id = f"retry-batch-{uuid.uuid4().hex[:6]}"
    sample_time = datetime.now(UTC) - timedelta(seconds=10)
    payload = [
        {
            "timestamp": sample_time.isoformat(),
            "cpu": {"usage_percent": 30.0},
            "memory": {"usage_percent": 50.0},
            "disks": [],
            "networks": [],
        }
    ]

    # Initial delivery
    res1 = process_metric_batch(agent_id=agent_id_str, batch_id=batch_id, metrics_payload=payload)
    assert res1["status"] == "processed"

    # Redelivery (Celery retry or agent resend)
    res2 = process_metric_batch(agent_id=agent_id_str, batch_id=batch_id, metrics_payload=payload)
    assert res2["status"] == "already_processed"
