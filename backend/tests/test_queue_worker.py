"""
OpsPulse Backend — Tests: Queue, Worker & Idempotency (Day 10)
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_agent_secret, hash_secret
from app.main import app
from app.models.agent import Agent, AgentStatus
from app.models.processed_batch import BatchStatus, ProcessedBatch
from app.workers.tasks import process_metric_batch


@pytest.fixture
async def registered_agent(db_session: AsyncSession) -> tuple[Agent, str]:
    """Provisions a test agent in PostgreSQL and returns (agent_instance, plaintext_secret)."""
    raw_secret = generate_agent_secret()
    agent = Agent(
        name="test-queue-node",
        hostname="queue-node-01.local",
        os_type="linux",
        agent_version="0.1.0",
        credential_hash=hash_secret(raw_secret),
        status=AgentStatus.ONLINE,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent, raw_secret


@pytest.mark.asyncio
async def test_ingest_dispatches_to_queue(registered_agent: tuple[Agent, str]) -> None:
    """Verifies that ingest endpoint dispatches the batch to Celery and returns 202."""
    agent, secret = registered_agent
    batch_id = str(uuid.uuid4())

    payload = {
        "agent_id": str(agent.id),
        "batch_id": batch_id,
        "metrics": [{"cpu": {"usage_percent": 25.0, "logical_cores": 4}}],
    }

    with patch("app.api.v1.metrics.process_metric_batch.delay") as mock_delay:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/api/v1/metrics/ingest",
                headers={"X-Agent-ID": str(agent.id), "X-Agent-Secret": secret},
                json=payload,
            )

        assert response.status_code == 202
        assert mock_delay.called
        call_kwargs = mock_delay.call_args.kwargs
        assert call_kwargs["agent_id"] == str(agent.id)
        assert call_kwargs["batch_id"] == batch_id
        assert len(call_kwargs["metrics_payload"]) == 1


@pytest.mark.asyncio
async def test_ingest_returns_503_on_queue_failure(registered_agent: tuple[Agent, str]) -> None:
    """Verifies that if Celery/Redis queue publication fails, API returns 503 so agent retains buffer."""
    agent, secret = registered_agent

    payload = {
        "agent_id": str(agent.id),
        "batch_id": str(uuid.uuid4()),
        "metrics": [{"cpu": {"usage_percent": 25.0, "logical_cores": 4}}],
    }

    with patch(
        "app.api.v1.metrics.process_metric_batch.delay",
        side_effect=ConnectionError("Cannot connect to Redis broker"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/api/v1/metrics/ingest",
                headers={"X-Agent-ID": str(agent.id), "X-Agent-Secret": secret},
                json=payload,
            )

        assert response.status_code == 503
        assert "temporarily unavailable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_worker_task_idempotency_deduplication(
    registered_agent: tuple[Agent, str], db_session: AsyncSession
) -> None:
    """Tests that process_metric_batch processes once, and duplicate delivery is recognized and skipped."""
    agent, _ = registered_agent
    batch_id = str(uuid.uuid4())
    sample_metrics = [{"cpu": {"usage_percent": 30.0, "logical_cores": 2}}]

    # 1. First execution -> PROCESSED
    result1 = process_metric_batch(
        agent_id=str(agent.id),
        batch_id=batch_id,
        metrics_payload=sample_metrics,
    )
    assert result1["status"] == "processed"
    assert result1["batch_id"] == batch_id

    # Verify database record
    stmt = select(ProcessedBatch).where(
        ProcessedBatch.agent_id == agent.id,
        ProcessedBatch.batch_id == batch_id,
    )
    db_res = await db_session.execute(stmt)
    record = db_res.scalar_one()
    assert record.status == BatchStatus.PROCESSED
    assert record.attempt_count == 1
    assert record.processed_at is not None

    # 2. Duplicate execution -> already_processed
    result2 = process_metric_batch(
        agent_id=str(agent.id),
        batch_id=batch_id,
        metrics_payload=sample_metrics,
    )
    assert result2["status"] == "already_processed"
    assert result2["batch_id"] == batch_id
