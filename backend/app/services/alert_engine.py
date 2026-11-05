"""
OpsPulse Backend — Alert Evaluation Engine

Evaluates active alert rules against recent agent metrics.
Handles:
- Comparison operators (>, >=, <, <=, ==)
- Evaluation windows and consecutive breach verification
- Dimension filtering and EACH / MAX aggregation
- Missing-data distinction from zero values
- Cooldown suppression and incident deduplication
- Auto-resolution when metrics recover
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.agent import Agent
from app.models.alert import (
    AlertOperator,
    AlertRule,
    DimensionAggregation,
)
from app.models.incident import (
    Incident,
    IncidentEvent,
    IncidentEventType,
    IncidentStatus,
)
from app.models.metric import MetricRecord

logger = logging.getLogger(__name__)


def evaluate_operator(value: float, operator: AlertOperator | str, threshold: float) -> bool:
    """Evaluates whether a value breaches a threshold given an operator."""
    op = AlertOperator(operator) if isinstance(operator, str) else operator

    if op == AlertOperator.GT:
        return value > threshold
    elif op == AlertOperator.GTE:
        return value >= threshold
    elif op == AlertOperator.LT:
        return value < threshold
    elif op == AlertOperator.LTE:
        return value <= threshold
    elif op == AlertOperator.EQ:
        return abs(value - threshold) < 1e-5
    return False


def _extract_metric_values(
    record: MetricRecord,
    metric_key: str,
) -> float | dict[str, float] | None:
    """
    Extracts scalar or dimensioned values from a MetricRecord based on metric_key.
    Returns None if the metric data is absent (missing data).
    """
    key = metric_key.lower().strip()

    # CPU metrics
    if key in ("cpu_percent", "cpu_usage_percent", "cpu"):
        return record.cpu_usage_percent

    # Memory metrics
    if key in ("memory_percent", "memory_usage_percent", "memory"):
        return record.memory_usage_percent

    # Disk metrics (dimensioned by mount_point)
    if key in ("disk_percent", "disk_usage_percent", "disk"):
        if not record.disks:
            return None
        return {d.mount_point: d.usage_percent for d in record.disks}

    # Network rate metrics (dimensioned by interface_name)
    if key in ("network_bytes_sent_rate", "network_tx_rate", "bytes_sent_per_sec"):
        if not record.networks:
            return None
        return {n.interface_name: n.bytes_sent_per_sec for n in record.networks}

    if key in ("network_bytes_recv_rate", "network_rx_rate", "bytes_recv_per_sec"):
        if not record.networks:
            return None
        return {n.interface_name: n.bytes_recv_per_sec for n in record.networks}

    return None


class AlertEngine:
    """Core evaluation engine for infrastructure alert rules and incident transitions."""

    @classmethod
    def evaluate_agent(
        cls,
        session: Session,
        agent_id: uuid.UUID,
        now: datetime | None = None,
    ) -> list[Incident]:
        """
        Evaluates all applicable active alert rules for an agent against stored recent metrics.
        Creates or updates incidents and auto-resolves recovered incidents.
        """
        if now is None:
            now = datetime.now(UTC)

        agent = session.get(Agent, agent_id)
        if not agent:
            logger.warning(f"Agent {agent_id} not found for alert evaluation")
            return []

        # 1. Fetch enabled rules applicable to this agent (or global rules)
        rules_stmt = select(AlertRule).where(
            AlertRule.enabled.is_(True),
            (AlertRule.agent_id.is_(None)) | (AlertRule.agent_id == agent_id),
        )
        rules = list(session.execute(rules_stmt).scalars().all())
        if not rules:
            return []

        # Find maximum evaluation window needed across all rules
        max_window = max(r.evaluation_window_seconds for r in rules)
        window_start = now - timedelta(seconds=max_window + 10)

        # 2. Query recent metric records for this agent
        records_stmt = (
            select(MetricRecord)
            .options(
                selectinload(MetricRecord.disks),
                selectinload(MetricRecord.networks),
            )
            .where(
                MetricRecord.agent_id == agent_id,
                MetricRecord.timestamp >= window_start,
                MetricRecord.timestamp <= now,
            )
            .order_by(MetricRecord.timestamp.asc())
        )
        records = list(session.execute(records_stmt).scalars().all())

        affected_incidents: list[Incident] = []

        for rule in rules:
            incidents = cls._evaluate_rule_for_agent(
                session=session,
                agent=agent,
                rule=rule,
                all_records=records,
                now=now,
            )
            affected_incidents.extend(incidents)

        return affected_incidents

    @classmethod
    def _evaluate_rule_for_agent(
        cls,
        session: Session,
        agent: Agent,
        rule: AlertRule,
        all_records: list[MetricRecord],
        now: datetime,
    ) -> list[Incident]:
        """Evaluates a single alert rule against metrics for an agent."""
        cutoff = now - timedelta(seconds=rule.evaluation_window_seconds)
        window_records = [r for r in all_records if r.timestamp >= cutoff]

        # Results mapping: dimension -> (breached: bool, latest_value: float)
        evaluation_results: dict[str | None, tuple[bool, float]] = {}

        is_dimensioned = rule.metric_key.lower().strip() in (
            "disk_percent",
            "disk_usage_percent",
            "disk",
            "network_bytes_sent_rate",
            "network_tx_rate",
            "bytes_sent_per_sec",
            "network_bytes_recv_rate",
            "network_rx_rate",
            "bytes_recv_per_sec",
        )

        if not is_dimensioned:
            # Scalar metric (CPU, Memory)
            values: list[float] = []
            for r in window_records:
                v = _extract_metric_values(r, rule.metric_key)
                if isinstance(v, (int, float)):
                    values.append(float(v))

            if len(values) >= rule.consecutive_breaches:
                breaches = [
                    evaluate_operator(v, rule.operator, rule.threshold)
                    for v in values[-rule.consecutive_breaches :]
                ]
                all_breached = all(breaches)
                evaluation_results[None] = (all_breached, values[-1])
            else:
                # Insufficient samples in evaluation window -> not breached
                if values:
                    evaluation_results[None] = (False, values[-1])
        else:
            # Dimensioned metric (Disk, Network)
            if rule.dimension_filter:
                dim = rule.dimension_filter
                dim_values: list[float] = []
                for r in window_records:
                    v = _extract_metric_values(r, rule.metric_key)
                    if isinstance(v, dict) and dim in v:
                        dim_values.append(v[dim])

                if len(dim_values) >= rule.consecutive_breaches:
                    breaches = [
                        evaluate_operator(v, rule.operator, rule.threshold)
                        for v in dim_values[-rule.consecutive_breaches :]
                    ]
                    evaluation_results[dim] = (all(breaches), dim_values[-1])
                elif dim_values:
                    evaluation_results[dim] = (False, dim_values[-1])
            else:
                # No dimension filter provided
                if rule.dimension_aggregation == DimensionAggregation.MAX:
                    # Take max value across dimensions per record
                    max_values: list[float] = []
                    for r in window_records:
                        v = _extract_metric_values(r, rule.metric_key)
                        if isinstance(v, dict) and v:
                            max_values.append(max(v.values()))

                    if len(max_values) >= rule.consecutive_breaches:
                        breaches = [
                            evaluate_operator(v, rule.operator, rule.threshold)
                            for v in max_values[-rule.consecutive_breaches :]
                        ]
                        evaluation_results[None] = (all(breaches), max_values[-1])
                    elif max_values:
                        evaluation_results[None] = (False, max_values[-1])
                else:
                    # DimensionAggregation.EACH: Evaluate each dimension independently
                    all_dims: set[str] = set()
                    for r in window_records:
                        v = _extract_metric_values(r, rule.metric_key)
                        if isinstance(v, dict):
                            all_dims.update(v.keys())

                    for dim in all_dims:
                        dim_values = []
                        for r in window_records:
                            v = _extract_metric_values(r, rule.metric_key)
                            if isinstance(v, dict) and dim in v:
                                dim_values.append(v[dim])

                        if len(dim_values) >= rule.consecutive_breaches:
                            breaches = [
                                evaluate_operator(val, rule.operator, rule.threshold)
                                for val in dim_values[-rule.consecutive_breaches :]
                            ]
                            evaluation_results[dim] = (all(breaches), dim_values[-1])
                        elif dim_values:
                            evaluation_results[dim] = (False, dim_values[-1])

        # 3. Apply state machine transitions & deduplication
        processed_incidents: list[Incident] = []

        for dimension, (breached, current_value) in evaluation_results.items():
            incident = cls._reconcile_incident_state(
                session=session,
                agent=agent,
                rule=rule,
                dimension=dimension,
                breached=breached,
                current_value=current_value,
                now=now,
            )
            if incident:
                processed_incidents.append(incident)

        return processed_incidents

    @classmethod
    def _reconcile_incident_state(
        cls,
        session: Session,
        agent: Agent,
        rule: AlertRule,
        dimension: str | None,
        breached: bool,
        current_value: float,
        now: datetime,
    ) -> Incident | None:
        """
        Reconciles active incident state with evaluation outcome.
        Handles deduplication, cooldown, creation, and auto-resolution.
        """
        # Query active incident: agent_id, rule_id, dimension in (OPEN, ACKNOWLEDGED, INVESTIGATING)
        active_stmt = select(Incident).where(
            Incident.agent_id == agent.id,
            Incident.rule_id == rule.id,
            Incident.dimension == dimension if dimension is not None else Incident.dimension.is_(None),
            Incident.status.in_([
                IncidentStatus.OPEN,
                IncidentStatus.ACKNOWLEDGED,
                IncidentStatus.INVESTIGATING,
            ]),
        )
        active_incident = session.execute(active_stmt).scalars().first()

        dim_str = f" [{dimension}]" if dimension else ""

        if breached:
            if active_incident is not None:
                # Deduplication: active incident exists, update last_seen_at
                active_incident.last_seen_at = now
                session.flush()
                return active_incident

            # Check cooldown against most recent resolved incident for this rule/dimension
            cooldown_stmt = select(func.max(Incident.resolved_at)).where(
                Incident.agent_id == agent.id,
                Incident.rule_id == rule.id,
                Incident.dimension == dimension if dimension is not None else Incident.dimension.is_(None),
                Incident.status == IncidentStatus.RESOLVED,
            )
            last_resolved = session.execute(cooldown_stmt).scalar()
            if last_resolved is not None:
                if last_resolved.tzinfo is None:
                    last_resolved = last_resolved.replace(tzinfo=UTC)
                cooldown_expires = last_resolved + timedelta(seconds=rule.cooldown_seconds)
                if now < cooldown_expires:
                    logger.info(
                        f"Alert suppressed by cooldown: rule={rule.name} agent={agent.name} until {cooldown_expires}"
                    )
                    return None

            # Create new incident
            new_incident = Incident(
                id=uuid.uuid4(),
                agent_id=agent.id,
                rule_id=rule.id,
                dimension=dimension,
                title=f"Alert: {rule.name} breached on {agent.name or agent.hostname}{dim_str}",
                description=(
                    f"Threshold breached: {rule.metric_key}{dim_str} is {current_value:.2f}% "
                    f"({rule.operator.value} {rule.threshold:.2f}%)"
                ),
                severity=rule.severity,
                status=IncidentStatus.OPEN,
                first_detected_at=now,
                last_seen_at=now,
            )
            session.add(new_incident)
            session.flush()

            # Record DETECTED event in timeline
            detect_event = IncidentEvent(
                id=uuid.uuid4(),
                incident_id=new_incident.id,
                event_type=IncidentEventType.DETECTED,
                message=(
                    f"Condition detected: {rule.metric_key}{dim_str} = {current_value:.2f} "
                    f"(breached threshold {rule.operator.value} {rule.threshold:.2f})"
                ),
                actor_user_id=None,
                metadata_={
                    "metric_key": rule.metric_key,
                    "value": current_value,
                    "threshold": rule.threshold,
                    "operator": rule.operator.value,
                    "dimension": dimension,
                },
                created_at=now,
            )
            new_incident.events.append(detect_event)
            session.add(new_incident)
            session.flush()
            logger.info(f"Created incident {new_incident.id} for agent {agent.id} rule {rule.name}")
            return new_incident

        else:
            # Condition is clear / healthy
            if active_incident is not None:
                # Auto-resolve the active incident
                active_incident.status = IncidentStatus.RESOLVED
                active_incident.resolved_at = now
                active_incident.last_seen_at = now

                resolve_event = IncidentEvent(
                    id=uuid.uuid4(),
                    incident_id=active_incident.id,
                    event_type=IncidentEventType.AUTO_CLEARED,
                    message=(
                        f"Alert condition cleared: {rule.metric_key}{dim_str} normalized to "
                        f"{current_value:.2f} (within threshold {rule.operator.value} {rule.threshold:.2f})"
                    ),
                    actor_user_id=None,
                    metadata_={
                        "metric_key": rule.metric_key,
                        "value": current_value,
                        "threshold": rule.threshold,
                        "dimension": dimension,
                    },
                    created_at=now,
                )
                active_incident.events.append(resolve_event)
                session.flush()
                logger.info(f"Auto-resolved incident {active_incident.id} for agent {agent.id} rule {rule.name}")
                return active_incident

        return None
