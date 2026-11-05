"""
OpsPulse Backend — Simulation Scenario & Pipeline Verification Tests (Day 24)

Verifies:
- CPU spike ingestion triggers alert rule evaluation
- Automatic incident creation with DETECTED event
- Recovery to normal usage auto-resolves incident with AUTO_CLEARED event
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select

from app.database.session import SyncSessionLocal
from app.models.agent import Agent, AgentStatus
from app.models.alert import AlertOperator, AlertRule, AlertSeverity
from app.models.incident import Incident, IncidentEventType, IncidentStatus
from app.workers.tasks import process_metric_batch


def test_simulation_cpu_spike_and_recovery_flow() -> None:
    """Simulates an agent undergoing a CPU spike followed by recovery."""
    with SyncSessionLocal() as session:
        # 1. Provision target agent
        agent = Agent(
            id=uuid.uuid4(),
            name="simulated-worker-01",
            hostname="worker01.sim.opspulse.local",
            credential_hash="hash",
            status=AgentStatus.ONLINE,
        )
        session.add(agent)

        # 2. Configure alert rule: CPU > 80% for 2 consecutive samples
        rule = AlertRule(
            id=uuid.uuid4(),
            name="High CPU Spike Detected",
            metric_key="cpu_percent",
            operator=AlertOperator.GT,
            threshold=80.0,
            severity=AlertSeverity.CRITICAL,
            evaluation_window_seconds=60,
            consecutive_breaches=2,
            cooldown_seconds=120,
            enabled=True,
            agent_id=agent.id,
        )
        session.add(rule)
        session.commit()
        agent_id_str = str(agent.id)

    base_time = datetime.now(UTC) - timedelta(seconds=40)

    # 3. Simulate Ingestion of Spiking Batch (2 consecutive samples > 80%)
    spike_batch = [
        {
            "timestamp": (base_time - timedelta(seconds=10)).isoformat(),
            "cpu": {"usage_percent": 88.5},
            "memory": {"usage_percent": 45.0},
            "disks": [],
            "networks": [],
        },
        {
            "timestamp": base_time.isoformat(),
            "cpu": {"usage_percent": 94.2},
            "memory": {"usage_percent": 46.0},
            "disks": [],
            "networks": [],
        },
    ]

    res = process_metric_batch(
        agent_id=agent_id_str,
        batch_id="sim-batch-001",
        metrics_payload=spike_batch,
    )
    assert res["status"] == "processed"
    assert res["records_created"] == 2

    # Verify Incident created in database
    with SyncSessionLocal() as session:
        inc_stmt = select(Incident).where(
            Incident.agent_id == uuid.UUID(agent_id_str),
            Incident.status == IncidentStatus.OPEN,
        )
        incident = session.execute(inc_stmt).scalars().first()
        assert incident is not None
        assert incident.severity == AlertSeverity.CRITICAL
        assert "High CPU Spike Detected" in incident.title
        incident_id = incident.id

        # Verify DETECTED event in timeline
        events = incident.events
        assert any(e.event_type == IncidentEventType.DETECTED for e in events)

    # 4. Simulate Recovery Batch (samples return to normal 25%)
    recovery_time = base_time + timedelta(seconds=20)
    recovery_batch = [
        {
            "timestamp": recovery_time.isoformat(),
            "cpu": {"usage_percent": 24.5},
            "memory": {"usage_percent": 42.0},
            "disks": [],
            "networks": [],
        },
    ]

    res_rec = process_metric_batch(
        agent_id=agent_id_str,
        batch_id="sim-batch-002",
        metrics_payload=recovery_batch,
    )
    assert res_rec["status"] == "processed"

    # Verify Incident transitioned to RESOLVED with AUTO_CLEARED event
    with SyncSessionLocal() as session:
        inc_refreshed = session.get(Incident, incident_id)
        assert inc_refreshed.status == IncidentStatus.RESOLVED
        assert inc_refreshed.resolved_at is not None

        events_refreshed = inc_refreshed.events
        assert any(e.event_type == IncidentEventType.AUTO_CLEARED for e in events_refreshed)
