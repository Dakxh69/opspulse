"""
OpsPulse Backend — Tests: Metric Persistence, Query APIs & Downsampling (Day 11)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_agent_secret, hash_secret
from app.main import app
from app.models.agent import Agent, AgentStatus
from app.models.metric import MetricAggregate, MetricRecord
from app.models.user import User, UserRole
from app.workers.tasks import cleanup_old_metrics, downsample_metrics, process_metric_batch


@pytest.fixture
async def authenticated_user_and_agent(
    db_session: AsyncSession,
) -> tuple[AsyncClient, Agent]:
    """Provides logged-in user HTTP client and a monitored agent entity."""
    user_email = f"metric_user_{uuid.uuid4().hex[:8]}@opspulse.local"
    user = User(
        email=user_email,
        password_hash=hash_secret("Password123!"),
        role=UserRole.OPERATOR,
        is_active=True,
    )
    raw_secret = generate_agent_secret()
    agent = Agent(
        name="storage-node-01",
        hostname="storage-01.local",
        os_type="linux",
        agent_version="0.1.0",
        credential_hash=hash_secret(raw_secret),
        status=AgentStatus.ONLINE,
    )
    db_session.add_all([user, agent])
    await db_session.commit()
    await db_session.refresh(agent)

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": user_email, "password": "Password123!"},
    )
    assert login_res.status_code == 200

    return client, agent


@pytest.mark.asyncio
async def test_worker_persists_raw_metrics(
    authenticated_user_and_agent: tuple[AsyncClient, Agent],
    db_session: AsyncSession,
) -> None:
    """Verifies that process_metric_batch transactionally writes MetricRecord, MetricDisk, and MetricNetwork."""
    _, agent = authenticated_user_and_agent
    batch_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    sample_payload = [
        {
            "timestamp": now_iso,
            "cpu": {"usage_percent": 55.5, "logical_cores": 4},
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
                    "device": "/dev/nvme0n1p2",
                    "fstype": "ext4",
                    "total_bytes": 500000000000,
                    "used_bytes": 250000000000,
                    "free_bytes": 250000000000,
                    "usage_percent": 50.0,
                }
            ],
            "networks": [
                {
                    "name": "eth0",
                    "bytes_sent": 100000,
                    "bytes_recv": 200000,
                    "packets_sent": 1000,
                    "packets_recv": 2000,
                    "errin": 0,
                    "errout": 0,
                    "dropin": 0,
                    "dropout": 0,
                    "bytes_sent_per_sec": 500.0,
                    "bytes_recv_per_sec": 1000.0,
                }
            ],
        }
    ]

    res = process_metric_batch(
        agent_id=str(agent.id),
        batch_id=batch_id,
        metrics_payload=sample_payload,
    )
    assert res["status"] == "processed"
    assert res["records_created"] == 1

    # Verify database persistence
    stmt = select(MetricRecord).where(MetricRecord.agent_id == agent.id)
    records = (await db_session.execute(stmt)).scalars().all()
    assert len(records) >= 1
    record = records[0]
    assert record.cpu_usage_percent == 55.5
    assert record.memory_usage_percent == 50.0
    assert len(record.disks) == 1
    assert record.disks[0].mount_point == "/"
    assert len(record.networks) == 1
    assert record.networks[0].interface_name == "eth0"


@pytest.mark.asyncio
async def test_metric_query_apis(
    authenticated_user_and_agent: tuple[AsyncClient, Agent],
    db_session: AsyncSession,
) -> None:
    """Verifies history, latest, and summary GET endpoints."""
    client, agent = authenticated_user_and_agent

    # Insert 3 consecutive samples
    now = datetime.now(UTC)
    for i, cpu in enumerate([20.0, 40.0, 60.0]):
        rec = MetricRecord(
            id=uuid.uuid4(),
            agent_id=agent.id,
            timestamp=now - timedelta(minutes=10 - i),
            cpu_usage_percent=cpu,
            memory_usage_percent=30.0 + i * 10,
        )
        db_session.add(rec)
    await db_session.commit()

    # 1. Query history
    res_hist = await client.get(f"/api/v1/metrics/{agent.id}?limit=10")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert len(hist_data) >= 3

    # 2. Query latest
    res_latest = await client.get(f"/api/v1/metrics/{agent.id}/latest")
    assert res_latest.status_code == 200
    latest_data = res_latest.json()
    assert latest_data["cpu_usage_percent"] == 60.0

    # 3. Query summary
    res_summary = await client.get(f"/api/v1/metrics/{agent.id}/summary?hours=1")
    assert res_summary.status_code == 200
    summary_data = res_summary.json()
    assert summary_data["sample_count"] >= 3
    assert summary_data["avg_cpu_percent"] == 40.0
    assert summary_data["min_cpu_percent"] == 20.0
    assert summary_data["max_cpu_percent"] == 60.0


@pytest.mark.asyncio
async def test_retention_and_downsampling_tasks(
    authenticated_user_and_agent: tuple[AsyncClient, Agent],
    db_session: AsyncSession,
) -> None:
    """Tests cleanup_old_metrics and downsample_metrics tasks."""
    _, agent = authenticated_user_and_agent

    # 1. Insert an expired record (> 8 days ago)
    old_time = datetime.now(UTC) - timedelta(days=9)
    expired_record = MetricRecord(
        id=uuid.uuid4(),
        agent_id=agent.id,
        timestamp=old_time,
        cpu_usage_percent=10.0,
        memory_usage_percent=10.0,
    )
    db_session.add(expired_record)
    await db_session.commit()

    # Run cleanup task
    cleanup_res = cleanup_old_metrics()
    assert cleanup_res["raw_records_deleted"] >= 1

    # Verify expired record deleted
    check_stmt = select(MetricRecord).where(MetricRecord.id == expired_record.id)
    assert (await db_session.execute(check_stmt)).scalar_one_or_none() is None

    # 2. Test downsampling recent records
    recent_rec = MetricRecord(
        id=uuid.uuid4(),
        agent_id=agent.id,
        timestamp=datetime.now(UTC) - timedelta(minutes=2),
        cpu_usage_percent=75.0,
        memory_usage_percent=80.0,
    )
    db_session.add(recent_rec)
    await db_session.commit()

    downsample_res = downsample_metrics(window_minutes=15)
    assert downsample_res["aggregates_created"] >= 1

    # Verify aggregate entry in DB
    agg_stmt = select(MetricAggregate).where(MetricAggregate.agent_id == agent.id)
    aggs = (await db_session.execute(agg_stmt)).scalars().all()
    assert len(aggs) >= 1
    assert aggs[0].metric_key == "cpu.usage_percent"
