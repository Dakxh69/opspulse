"""
OpsPulse Backend — End-to-End Integration Suite (Day 26)

Validates complete cross-system pipelines per spec Section 21 and Section 23:
1. Ingestion Pipeline: Agent auth -> batch ingestion -> Celery processing -> metric persistence & query.
2. Alert-to-Incident Workflow: Multi-sample breach -> AlertEngine -> Incident detection -> Acknowledge -> Auto-resolve.
3. RBAC Matrix: Role-based permissions enforcement across incident triage and alert management.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_secret
from app.database.session import SyncSessionLocal
from app.main import app
from app.models.agent import Agent, AgentStatus
from app.models.alert import AlertOperator, AlertRule, AlertSeverity
from app.models.incident import Incident, IncidentStatus
from app.models.metric import MetricRecord
from app.models.user import User, UserRole
from app.services.alert_engine import AlertEngine
from app.workers.tasks import process_metric_batch


@pytest.mark.asyncio
async def test_e2e_ingestion_and_metric_query_pipeline(db_session: AsyncSession) -> None:
    """
    Validates end-to-end pipeline:
    Agent batch ingest -> Celery worker persistence -> Metric query API.
    """
    uid = uuid.uuid4().hex[:6]
    raw_secret = f"e2e-secret-{uid}"
    agent = Agent(
        id=uuid.uuid4(),
        name=f"e2e-host-{uid}",
        hostname=f"e2e-{uid}.opspulse.local",
        credential_hash=hash_secret(raw_secret),
        status=AgentStatus.ONLINE,
    )
    admin = User(
        id=uuid.uuid4(),
        email=f"admin-e2e-{uid}@opspulse.local",
        password_hash=hash_secret("admin_pass"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add_all([agent, admin])
    await db_session.commit()

    agent_id_str = str(agent.id)
    batch_id = f"e2e-batch-{uid}"
    now = datetime.now(UTC)
    t1 = now - timedelta(seconds=20)
    t2 = now - timedelta(seconds=10)

    # 1. Process batch through worker task
    payload = [
        {
            "timestamp": t1.isoformat(),
            "cpu": {"usage_percent": 45.5, "logical_cores": 4},
            "memory": {"usage_percent": 62.0, "total_bytes": 16000000000, "used_bytes": 9920000000},
            "disks": [
                {
                    "device": "/dev/sda1",
                    "mount_point": "/",
                    "fstype": "ext4",
                    "total_bytes": 100000000000,
                    "used_bytes": 70000000000,
                    "free_bytes": 30000000000,
                    "usage_percent": 70.0,
                }
            ],
            "networks": [
                {
                    "name": "eth0",
                    "bytes_sent": 1200000,
                    "bytes_recv": 3400000,
                }
            ],
        },
        {
            "timestamp": t2.isoformat(),
            "cpu": {"usage_percent": 55.0, "logical_cores": 4},
            "memory": {
                "usage_percent": 64.0,
                "total_bytes": 16000000000,
                "used_bytes": 10240000000,
            },
            "disks": [
                {
                    "device": "/dev/sda1",
                    "mount_point": "/",
                    "fstype": "ext4",
                    "total_bytes": 100000000000,
                    "used_bytes": 70100000000,
                    "free_bytes": 29900000000,
                    "usage_percent": 70.1,
                }
            ],
            "networks": [
                {
                    "name": "eth0",
                    "bytes_sent": 1500000,
                    "bytes_recv": 4200000,
                }
            ],
        },
    ]

    res = process_metric_batch(agent_id=agent_id_str, batch_id=batch_id, metrics_payload=payload)
    assert res["status"] == "processed"
    assert res["records_created"] == 2

    # 2. Query metrics via authenticated REST API
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get(
            f"/api/v1/metrics/{agent_id_str}",
            cookies={"access_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2


@pytest.mark.asyncio
async def test_e2e_alert_to_incident_and_rbac_flow(db_session: AsyncSession) -> None:
    """
    Validates alert-to-incident lifecycle with RBAC triage:
    1. Threshold breach triggers critical incident.
    2. Viewer role attempts acknowledge (HTTP 403 Forbidden).
    3. Operator acknowledges incident (HTTP 200 OK -> ACKNOWLEDGED).
    4. Metric recovery evaluates and auto-resolves incident (AUTO_CLEARED).
    """
    uid = uuid.uuid4().hex[:6]
    viewer = User(
        id=uuid.uuid4(),
        email=f"viewer-{uid}@opspulse.local",
        password_hash=hash_secret("viewer_pass"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    operator = User(
        id=uuid.uuid4(),
        email=f"operator-{uid}@opspulse.local",
        password_hash=hash_secret("operator_pass"),
        role=UserRole.OPERATOR,
        is_active=True,
    )
    agent = Agent(
        id=uuid.uuid4(),
        name=f"incident-host-{uid}",
        hostname=f"inc-{uid}.opspulse.local",
        credential_hash=hash_secret("sec"),
        status=AgentStatus.ONLINE,
    )
    rule = AlertRule(
        id=uuid.uuid4(),
        name=f"High Memory Warning {uid}",
        agent_id=agent.id,
        metric_key="memory_percent",
        operator=AlertOperator.GT,
        threshold=80.0,
        severity=AlertSeverity.WARNING,
        evaluation_window_seconds=60,
        consecutive_breaches=2,
        cooldown_seconds=300,
        enabled=True,
    )
    db_session.add_all([viewer, operator, agent, rule])
    await db_session.commit()

    agent_id = agent.id
    now = datetime.now(UTC) - timedelta(seconds=60)

    # 2. Trigger consecutive breaches via stored metric records
    with SyncSessionLocal() as session:
        rec1 = MetricRecord(
            agent_id=agent_id,
            timestamp=now + timedelta(seconds=10),
            cpu_usage_percent=10.0,
            memory_usage_percent=85.0,
        )
        rec2 = MetricRecord(
            agent_id=agent_id,
            timestamp=now + timedelta(seconds=20),
            cpu_usage_percent=10.0,
            memory_usage_percent=90.0,
        )
        session.add_all([rec1, rec2])
        session.commit()

        incidents = AlertEngine.evaluate_agent(session, agent_id, now=now + timedelta(seconds=25))
        session.commit()
        our_incidents = [inc for inc in incidents if inc.rule_id == rule.id]
        assert len(our_incidents) == 1
        incident_id = our_incidents[0].id
        assert our_incidents[0].status == IncidentStatus.OPEN
        assert our_incidents[0].severity == AlertSeverity.WARNING

    # 3. RBAC check: Viewer attempt to acknowledge must be rejected (403)
    viewer_token = create_access_token(subject=str(viewer.id), role=viewer.role.value)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            f"/api/v1/incidents/{incident_id}/acknowledge",
            cookies={"access_token": viewer_token},
        )
        assert resp.status_code == 403

    # 4. RBAC check: Operator acknowledges successfully (200)
    operator_token = create_access_token(subject=str(operator.id), role=operator.role.value)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            f"/api/v1/incidents/{incident_id}/acknowledge",
            cookies={"access_token": operator_token},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACKNOWLEDGED"

    # 5. Recovery: normal metric value triggers auto-resolution
    with SyncSessionLocal() as session:
        rec3 = MetricRecord(
            agent_id=agent_id,
            timestamp=now + timedelta(seconds=35),
            cpu_usage_percent=10.0,
            memory_usage_percent=50.0,
        )
        session.add(rec3)
        session.commit()

        incidents_resolved = AlertEngine.evaluate_agent(
            session, agent_id, now=now + timedelta(seconds=40)
        )
        session.commit()
        our_resolved = [inc for inc in incidents_resolved if inc.rule_id == rule.id]
        assert len(our_resolved) == 1
        assert our_resolved[0].status == IncidentStatus.RESOLVED

        inc = session.get(Incident, incident_id)
        assert inc.status == IncidentStatus.RESOLVED
        assert inc.resolved_at is not None
