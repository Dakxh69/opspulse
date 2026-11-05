"""
OpsPulse — Demo Data Seeder for Visual Dashboard & Video Tour

Seeds realistic agents, historical telemetry metrics, incidents, and alert rules.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
import random

from app.core.security import hash_secret
from app.database.session import SyncSessionLocal
from app.models.agent import Agent, AgentStatus
from app.models.alert import AlertOperator, AlertRule, AlertSeverity
from app.models.incident import Incident, IncidentEvent, IncidentEventType, IncidentStatus
from app.models.metric import MetricDisk, MetricNetwork, MetricRecord
from app.models.user import User, UserRole


def seed_demo_data() -> None:
    with SyncSessionLocal() as session:
        # 1. Admin User
        admin_email = "admin@opspulse.local"
        existing_user = session.query(User).filter(User.email == admin_email).first()
        if not existing_user:
            admin = User(
                id=uuid.uuid4(),
                email=admin_email,
                password_hash=hash_secret("adminpassword"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(admin)
            session.flush()
            user_id = admin.id
        else:
            user_id = existing_user.id

        # 2. Alert Rules
        rules_data = [
            ("High CPU Sustained", "cpu_percent", AlertOperator.GT, 80.0, AlertSeverity.CRITICAL, 60, 2),
            ("RAM Exhaustion Warning", "memory_percent", AlertOperator.GT, 85.0, AlertSeverity.WARNING, 120, 2),
            ("Disk Root Capacity Alert", "disk_percent", AlertOperator.GT, 90.0, AlertSeverity.CRITICAL, 300, 1),
            ("Network Packet Drop Surge", "network_tx_rate", AlertOperator.GT, 50000000.0, AlertSeverity.WARNING, 60, 2),
        ]
        created_rules = []
        for name, key, op, th, sev, win, cb in rules_data:
            existing_rule = session.query(AlertRule).filter(AlertRule.name == name).first()
            if not existing_rule:
                rule = AlertRule(
                    id=uuid.uuid4(),
                    name=name,
                    metric_key=key,
                    operator=op,
                    threshold=th,
                    severity=sev,
                    evaluation_window_seconds=win,
                    consecutive_breaches=cb,
                    cooldown_seconds=300,
                    enabled=True,
                )
                session.add(rule)
                session.flush()
                created_rules.append(rule)
            else:
                created_rules.append(existing_rule)

        # 3. Agents & Host Inventory
        now = datetime.now(UTC)
        agents_data = [
            ("web-prod-01", "web-prod-01.opspulse.local", AgentStatus.ONLINE, now - timedelta(seconds=12)),
            ("db-cluster-01", "db-cluster-01.opspulse.local", AgentStatus.ONLINE, now - timedelta(seconds=8)),
            ("worker-queue-01", "worker-queue-01.opspulse.local", AgentStatus.DEGRADED, now - timedelta(seconds=75)),
            ("backup-srv-01", "backup-srv-01.opspulse.local", AgentStatus.OFFLINE, now - timedelta(seconds=350)),
        ]

        created_agents = []
        for name, hostname, status, hb in agents_data:
            agent = session.query(Agent).filter(Agent.hostname == hostname).first()
            if not agent:
                agent = Agent(
                    id=uuid.uuid4(),
                    name=name,
                    hostname=hostname,
                    credential_hash=hash_secret("demo-secret"),
                    status=status,
                    last_heartbeat=hb,
                )
                session.add(agent)
                session.flush()
            else:
                agent.status = status
                agent.last_heartbeat = hb
            created_agents.append(agent)

        # 4. Generate Metric History for web-prod-01 & db-cluster-01
        for agent in created_agents[:2]:
            base_cpu = 35.0 if "web" in agent.name else 55.0
            base_mem = 45.0 if "web" in agent.name else 70.0

            # 30 samples over the last 30 minutes
            for i in range(30):
                t_sample = now - timedelta(minutes=30 - i)
                rec = MetricRecord(
                    id=uuid.uuid4(),
                    agent_id=agent.id,
                    timestamp=t_sample,
                    cpu_usage_percent=round(base_cpu + random.uniform(-10.0, 15.0), 1),
                    memory_usage_percent=round(base_mem + random.uniform(-5.0, 8.0), 1),
                )
                session.add(rec)
                session.flush()

                # Add disk
                d = MetricDisk(
                    id=uuid.uuid4(),
                    record_id=rec.id,
                    mount_point="/",
                    device="/dev/sda1",
                    fstype="ext4",
                    total_bytes=100000000000,
                    used_bytes=65000000000,
                    free_bytes=35000000000,
                    usage_percent=65.0,
                )
                session.add(d)

                # Add network
                net = MetricNetwork(
                    id=uuid.uuid4(),
                    record_id=rec.id,
                    interface_name="eth0",
                    bytes_sent=int(15000000 + i * 250000),
                    bytes_recv=int(45000000 + i * 500000),
                )
                session.add(net)

        # 5. Incidents
        incidents_data = [
            (
                created_agents[2].id,  # worker-queue-01
                created_rules[0].id,
                "CPU Threshold Sustained Breach (>80%)",
                "cpu",
                AlertSeverity.CRITICAL,
                IncidentStatus.OPEN,
                "CPU utilization has sustained at 94.2% across consecutive 60s windows.",
                now - timedelta(minutes=14),
            ),
            (
                created_agents[1].id,  # db-cluster-01
                created_rules[1].id,
                "High Memory Pressure Warning (>85%)",
                "memory",
                AlertSeverity.WARNING,
                IncidentStatus.ACKNOWLEDGED,
                "PostgreSQL shared_buffers memory consumption approaching threshold limit.",
                now - timedelta(minutes=45),
            ),
            (
                created_agents[0].id,  # web-prod-01
                created_rules[3].id,
                "Transient Ingress Traffic Spike",
                "network",
                AlertSeverity.WARNING,
                IncidentStatus.RESOLVED,
                "Interface eth0 experienced temporary traffic surge; normalized automatically.",
                now - timedelta(hours=2),
            ),
        ]

        for ag_id, r_id, title, dim, sev, st, desc, started in incidents_data:
            existing_inc = session.query(Incident).filter(Incident.title == title).first()
            if not existing_inc:
                inc = Incident(
                    id=uuid.uuid4(),
                    agent_id=ag_id,
                    rule_id=r_id,
                    title=title,
                    dimension=dim,
                    severity=sev,
                    status=st,
                    description=desc,
                    first_detected_at=started,
                    last_seen_at=now - timedelta(minutes=2) if st != IncidentStatus.RESOLVED else started + timedelta(minutes=20),
                    resolved_at=now - timedelta(minutes=90) if st == IncidentStatus.RESOLVED else None,
                )
                session.add(inc)
                session.flush()

                # Add event timeline
                e1 = IncidentEvent(
                    id=uuid.uuid4(),
                    incident_id=inc.id,
                    event_type=IncidentEventType.DETECTED,
                    message="Automated AlertEngine detection from metric stream.",
                    actor_user_id=None,
                    created_at=started,
                )
                session.add(e1)

                if st in (IncidentStatus.ACKNOWLEDGED, IncidentStatus.RESOLVED):
                    e2 = IncidentEvent(
                        id=uuid.uuid4(),
                        incident_id=inc.id,
                        event_type=IncidentEventType.ACKNOWLEDGED,
                        message="Triage investigation initiated by on-call SRE.",
                        actor_user_id=user_id,
                        created_at=started + timedelta(minutes=5),
                    )
                    session.add(e2)

                if st == IncidentStatus.RESOLVED:
                    e3 = IncidentEvent(
                        id=uuid.uuid4(),
                        incident_id=inc.id,
                        event_type=IncidentEventType.AUTO_CLEARED,
                        message="Telemetry returned to nominal baseline; auto-cleared.",
                        actor_user_id=None,
                        created_at=started + timedelta(minutes=20),
                    )
                    session.add(e3)

        session.commit()
        print("Successfully seeded demo data: Admin, Agents, Metrics, Rules, Incidents!")


if __name__ == "__main__":
    seed_demo_data()
