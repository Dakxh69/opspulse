"""
OpsPulse Backend — Tests: Heartbeat & Ingestion API (Day 9)
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_agent_secret, hash_secret
from app.main import app
from app.models.agent import Agent, AgentStatus


@pytest.fixture
async def registered_agent(db_session: AsyncSession) -> tuple[Agent, str]:
    """Provisions a test agent in PostgreSQL and returns (agent_instance, plaintext_secret)."""
    raw_secret = generate_agent_secret()
    agent = Agent(
        name="test-telemetry-node",
        hostname="telemetry-01.local",
        os_type="linux",
        agent_version="0.1.0",
        credential_hash=hash_secret(raw_secret),
        status=AgentStatus.OFFLINE,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent, raw_secret


@pytest.mark.asyncio
async def test_heartbeat_lifecycle(
    registered_agent: tuple[Agent, str], db_session: AsyncSession
) -> None:
    """Verifies that POST /api/v1/agents/heartbeat updates last_heartbeat and transitions status to ONLINE."""
    agent, secret = registered_agent

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # 1. Unauthenticated request -> 401
        res_unauth = await client.post("/api/v1/agents/heartbeat")
        assert res_unauth.status_code == 401

        # 2. Invalid secret -> 401
        res_bad_sec = await client.post(
            "/api/v1/agents/heartbeat",
            headers={"X-Agent-ID": str(agent.id), "X-Agent-Secret": "wrong_secret"},
        )
        assert res_bad_sec.status_code == 401

        # 3. Valid authenticated heartbeat -> 204
        res_ok = await client.post(
            "/api/v1/agents/heartbeat",
            headers={"X-Agent-ID": str(agent.id), "X-Agent-Secret": secret},
        )
        assert res_ok.status_code == 204

    # Refresh agent from database to reflect commits from the heartbeat request session
    await db_session.refresh(agent)
    assert agent.status == AgentStatus.ONLINE
    assert agent.last_heartbeat is not None


@pytest.mark.asyncio
async def test_metrics_ingest_success(registered_agent: tuple[Agent, str]) -> None:
    """Validates structural ingestion and 202 Accepted response for well-formed metric batch."""
    agent, secret = registered_agent
    batch_id = str(uuid.uuid4())

    payload = {
        "agent_id": str(agent.id),
        "batch_id": batch_id,
        "metrics": [
            {
                "timestamp": "2026-11-05T08:00:00Z",
                "cpu": {
                    "usage_percent": 45.2,
                    "per_core_percent": [40.0, 50.4],
                    "logical_cores": 2,
                    "physical_cores": 2,
                    "load_average": {"load_1m": 0.5, "load_5m": 0.4, "load_15m": 0.3},
                },
                "memory": {
                    "total_bytes": 16000000000,
                    "used_bytes": 8000000000,
                    "available_bytes": 8000000000,
                    "free_bytes": 4000000000,
                    "usage_percent": 50.0,
                },
                "disks": [
                    {
                        "mount_point": "/",
                        "device": "/dev/sda1",
                        "fstype": "ext4",
                        "total_bytes": 100000000000,
                        "used_bytes": 40000000000,
                        "free_bytes": 60000000000,
                        "usage_percent": 40.0,
                    }
                ],
                "networks": [
                    {
                        "name": "eth0",
                        "bytes_sent": 1000000,
                        "bytes_recv": 2000000,
                        "packets_sent": 5000,
                        "packets_recv": 8000,
                        "errin": 0,
                        "errout": 0,
                        "dropin": 0,
                        "dropout": 0,
                        "bytes_sent_per_sec": 1024.0,
                        "bytes_recv_per_sec": 2048.0,
                    }
                ],
            }
        ],
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/metrics/ingest",
            headers={"X-Agent-ID": str(agent.id), "X-Agent-Secret": secret},
            json=payload,
        )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["batch_id"] == batch_id
    assert data["samples_received"] == 1


@pytest.mark.asyncio
async def test_metrics_ingest_spoofed_agent_id_rejected(
    registered_agent: tuple[Agent, str],
) -> None:
    """Rejects request with 400 when payload agent_id differs from authenticated agent headers."""
    agent, secret = registered_agent
    spoofed_id = str(uuid.uuid4())

    payload = {
        "agent_id": spoofed_id,
        "batch_id": str(uuid.uuid4()),
        "metrics": [{"cpu": {"usage_percent": 10.0, "logical_cores": 1}}],
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/metrics/ingest",
            headers={"X-Agent-ID": str(agent.id), "X-Agent-Secret": secret},
            json=payload,
        )

    assert response.status_code == 400
    assert "Payload agent_id does not match" in response.json()["detail"]


@pytest.mark.asyncio
async def test_metrics_ingest_empty_batch_rejected(registered_agent: tuple[Agent, str]) -> None:
    """Empty metrics array is rejected by Pydantic validation (422 Unprocessable Entity)."""
    agent, secret = registered_agent

    payload = {
        "agent_id": str(agent.id),
        "batch_id": str(uuid.uuid4()),
        "metrics": [],
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/metrics/ingest",
            headers={"X-Agent-ID": str(agent.id), "X-Agent-Secret": secret},
            json=payload,
        )

    assert response.status_code == 422
