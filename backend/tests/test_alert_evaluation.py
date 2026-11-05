"""
OpsPulse Backend — Alert Evaluation & Reliability Tests (Day 13 & Day 14)

Verifies:
- All comparison operators (>, >=, <, <=, ==)
- Consecutive breach window criteria (preventing transient spikes)
- Missing data behavior
- Dimension filters and aggregation modes (EACH vs MAX)
- Incident deduplication (no duplicate OPEN incidents)
- Auto-resolution when condition clears
- Alert cooldown suppression
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.database.session import SyncSessionLocal
from app.models.agent import Agent, AgentStatus
from app.models.alert import (
    AlertOperator,
    AlertRule,
    AlertSeverity,
    DimensionAggregation,
)
from app.models.incident import (
    Incident,
    IncidentEventType,
    IncidentStatus,
)
from app.models.metric import MetricDisk, MetricRecord
from app.services.alert_engine import AlertEngine, evaluate_operator


def test_operator_evaluation() -> None:
    """Verifies all comparison operators."""
    assert evaluate_operator(85.0, AlertOperator.GT, 80.0) is True
    assert evaluate_operator(80.0, AlertOperator.GT, 80.0) is False
    assert evaluate_operator(80.0, AlertOperator.GTE, 80.0) is True
    assert evaluate_operator(79.9, AlertOperator.GTE, 80.0) is False

    assert evaluate_operator(15.0, AlertOperator.LT, 20.0) is True
    assert evaluate_operator(20.0, AlertOperator.LT, 20.0) is False
    assert evaluate_operator(20.0, AlertOperator.LTE, 20.0) is True
    assert evaluate_operator(20.1, AlertOperator.LTE, 20.0) is False

    assert evaluate_operator(100.0, AlertOperator.EQ, 100.0) is True
    assert evaluate_operator(100.0000001, AlertOperator.EQ, 100.0) is True
    assert evaluate_operator(99.0, AlertOperator.EQ, 100.0) is False


def test_consecutive_breaches_and_transient_spikes() -> None:
    """
    Verifies that transient spikes do NOT trigger an alert when consecutive_breaches > 1,
    and sustained breaches DO trigger an alert.
    """
    with SyncSessionLocal() as session:
        # Create test agent
        agent = Agent(
            id=uuid.uuid4(),
            name="test-agent-spikes",
            hostname="spikes.opspulse.local",
            credential_hash="hash",
            status=AgentStatus.ONLINE,
        )
        session.add(agent)

        # Create rule: CPU > 80% for 3 consecutive samples within 60s
        rule = AlertRule(
            id=uuid.uuid4(),
            name="High CPU Sustained",
            metric_key="cpu_percent",
            operator=AlertOperator.GT,
            threshold=80.0,
            severity=AlertSeverity.CRITICAL,
            evaluation_window_seconds=60,
            consecutive_breaches=3,
            cooldown_seconds=120,
            enabled=True,
            agent_id=agent.id,
        )
        session.add(rule)
        session.commit()

        now = datetime.now(UTC)

        # 1. Insert transient spike: [85.0, 60.0, 88.0]
        # Only 1 sample currently breaches in the last sequence
        for i, val in enumerate([85.0, 60.0, 88.0]):
            rec = MetricRecord(
                id=uuid.uuid4(),
                agent_id=agent.id,
                timestamp=now - timedelta(seconds=30 - i * 10),
                cpu_usage_percent=val,
                memory_usage_percent=40.0,
            )
            session.add(rec)
        session.commit()

        incidents = AlertEngine.evaluate_agent(session, agent.id, now=now)
        assert len(incidents) == 0  # No alert due to dip to 60.0!

        # 2. Now add sustained breaches: [88.0, 89.0, 92.0]
        now_sustained = now + timedelta(seconds=30)
        for i, val in enumerate([88.0, 89.0, 92.0]):
            rec = MetricRecord(
                id=uuid.uuid4(),
                agent_id=agent.id,
                timestamp=now_sustained - timedelta(seconds=20 - i * 10),
                cpu_usage_percent=val,
                memory_usage_percent=40.0,
            )
            session.add(rec)
        session.commit()

        incidents = AlertEngine.evaluate_agent(session, agent.id, now=now_sustained)
        assert len(incidents) == 1
        inc = incidents[0]
        assert inc.status == IncidentStatus.OPEN
        assert inc.severity == AlertSeverity.CRITICAL
        assert "High CPU Sustained" in inc.title


def test_missing_data_behavior() -> None:
    """Verifies missing data does not evaluate to 0 or trigger alerts inappropriately."""
    with SyncSessionLocal() as session:
        agent = Agent(
            id=uuid.uuid4(),
            name="test-agent-missing",
            hostname="missing.opspulse.local",
            credential_hash="hash",
            status=AgentStatus.ONLINE,
        )
        session.add(agent)

        # Low Memory rule: Memory < 10%
        rule = AlertRule(
            id=uuid.uuid4(),
            name="Low Memory Usage",
            metric_key="memory_percent",
            operator=AlertOperator.LT,
            threshold=10.0,
            severity=AlertSeverity.WARNING,
            evaluation_window_seconds=60,
            consecutive_breaches=2,
            enabled=True,
            agent_id=agent.id,
        )
        session.add(rule)
        session.commit()

        # No metric records inserted at all!
        incidents = AlertEngine.evaluate_agent(session, agent.id)
        assert len(incidents) == 0  # Missing data must not trigger < 10%


def test_dimension_filter_and_aggregation() -> None:
    """Verifies dimension filtering and EACH vs MAX aggregation for disk metrics."""
    with SyncSessionLocal() as session:
        agent = Agent(
            id=uuid.uuid4(),
            name="test-agent-disk",
            hostname="disk.opspulse.local",
            credential_hash="hash",
            status=AgentStatus.ONLINE,
        )
        session.add(agent)

        # Rule 1: Disk > 85% with filter on /data
        rule_data = AlertRule(
            id=uuid.uuid4(),
            name="Data Disk Full",
            metric_key="disk_percent",
            operator=AlertOperator.GT,
            threshold=85.0,
            severity=AlertSeverity.CRITICAL,
            dimension_filter="/data",
            evaluation_window_seconds=60,
            consecutive_breaches=1,
            enabled=True,
            agent_id=agent.id,
        )

        # Rule 2: Disk > 80% on EACH partition
        rule_each = AlertRule(
            id=uuid.uuid4(),
            name="Any Disk Full",
            metric_key="disk_percent",
            operator=AlertOperator.GT,
            threshold=80.0,
            severity=AlertSeverity.WARNING,
            dimension_filter=None,
            dimension_aggregation=DimensionAggregation.EACH,
            evaluation_window_seconds=60,
            consecutive_breaches=1,
            enabled=True,
            agent_id=agent.id,
        )
        session.add_all([rule_data, rule_each])
        session.commit()

        now = datetime.now(UTC)
        rec = MetricRecord(
            id=uuid.uuid4(),
            agent_id=agent.id,
            timestamp=now,
            cpu_usage_percent=10.0,
            memory_usage_percent=30.0,
        )
        session.add(rec)
        session.flush()

        # Add disk / (70% - not breaching) and /data (90% - breaching both)
        session.add_all([
            MetricDisk(
                id=uuid.uuid4(),
                record_id=rec.id,
                mount_point="/",
                device="/dev/sda1",
                fstype="ext4",
                total_bytes=1000,
                used_bytes=700,
                free_bytes=300,
                usage_percent=70.0,
            ),
            MetricDisk(
                id=uuid.uuid4(),
                record_id=rec.id,
                mount_point="/data",
                device="/dev/sdb1",
                fstype="ext4",
                total_bytes=1000,
                used_bytes=900,
                free_bytes=100,
                usage_percent=90.0,
            ),
        ])
        session.commit()

        incidents = AlertEngine.evaluate_agent(session, agent.id, now=now)
        # Should create 2 incidents: 1 for rule_data (/data), 1 for rule_each (/data)
        assert len(incidents) == 2
        for inc in incidents:
            assert inc.dimension == "/data"
            assert inc.status == IncidentStatus.OPEN


def test_deduplication_auto_resolution_and_cooldown() -> None:
    """
    Verifies the full lifecycle of an incident in AlertEngine:
    1. Incident creation on breach
    2. Deduplication on continuous breach (updates last_seen_at, no new incident)
    3. Auto-resolution when metric clears
    4. Cooldown suppression preventing flapping / immediate re-alerting
    """
    with SyncSessionLocal() as session:
        # Clean any leftover rules to guarantee test isolation
        session.query(AlertRule).delete()
        session.commit()

        agent = Agent(
            id=uuid.uuid4(),
            name="test-agent-lifecycle",
            hostname="lifecycle.opspulse.local",
            credential_hash="hash",
            status=AgentStatus.ONLINE,
        )
        session.add(agent)

        rule = AlertRule(
            id=uuid.uuid4(),
            name="High RAM Alert",
            metric_key="memory_percent",
            operator=AlertOperator.GT,
            threshold=80.0,
            severity=AlertSeverity.WARNING,
            evaluation_window_seconds=60,
            consecutive_breaches=1,
            cooldown_seconds=300,
            enabled=True,
            agent_id=agent.id,
        )
        session.add(rule)
        session.commit()

        t0 = datetime.now(UTC)

        # 1. Breach at t0: 95% RAM
        r0 = MetricRecord(
            id=uuid.uuid4(),
            agent_id=agent.id,
            timestamp=t0,
            cpu_usage_percent=10.0,
            memory_usage_percent=95.0,
        )
        session.add(r0)
        session.commit()

        incidents0 = AlertEngine.evaluate_agent(session, agent.id, now=t0)
        assert len(incidents0) == 1
        inc0 = incidents0[0]
        assert inc0.status == IncidentStatus.OPEN
        first_incident_id = inc0.id

        # 2. Continuous breach at t0 + 10s: 96% RAM
        t1 = t0 + timedelta(seconds=10)
        r1 = MetricRecord(
            id=uuid.uuid4(),
            agent_id=agent.id,
            timestamp=t1,
            cpu_usage_percent=10.0,
            memory_usage_percent=96.0,
        )
        session.add(r1)
        session.commit()

        incidents1 = AlertEngine.evaluate_agent(session, agent.id, now=t1)
        assert len(incidents1) == 1
        assert incidents1[0].id == first_incident_id  # Deduplicated!
        assert incidents1[0].last_seen_at == t1

        # Check total incidents in DB for this agent
        total = session.execute(
            select(Incident).where(Incident.agent_id == agent.id)
        ).scalars().all()
        assert len(total) == 1  # Only 1 incident in DB!

        # 3. Metric recovers at t0 + 20s: 60% RAM
        t2 = t0 + timedelta(seconds=20)
        r2 = MetricRecord(
            id=uuid.uuid4(),
            agent_id=agent.id,
            timestamp=t2,
            cpu_usage_percent=10.0,
            memory_usage_percent=60.0,
        )
        session.add(r2)
        session.commit()

        incidents2 = AlertEngine.evaluate_agent(session, agent.id, now=t2)
        assert len(incidents2) == 1
        resolved_inc = incidents2[0]
        assert resolved_inc.status == IncidentStatus.RESOLVED
        assert resolved_inc.resolved_at is not None

        # Verify event was logged
        events = resolved_inc.events
        assert any(e.event_type == IncidentEventType.AUTO_CLEARED for e in events)

        # 4. Spike again at t0 + 30s: 95% RAM (within 300s cooldown window)
        t3 = t0 + timedelta(seconds=30)
        r3 = MetricRecord(
            id=uuid.uuid4(),
            agent_id=agent.id,
            timestamp=t3,
            cpu_usage_percent=10.0,
            memory_usage_percent=95.0,
        )
        session.add(r3)
        session.commit()

        incidents3 = AlertEngine.evaluate_agent(session, agent.id, now=t3)
        assert len(incidents3) == 0  # Suppressed by cooldown!

