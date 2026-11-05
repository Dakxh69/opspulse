"""
OpsPulse Backend — Alert Rule Endpoints

Provides CRUD operations and RBAC authorization for alert rules (Day 12).
Adheres strictly to spec Section 12 and Section 18.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database.session import get_db
from app.models.agent import Agent
from app.models.alert import AlertRule, AlertSeverity
from app.models.user import User, UserRole
from app.schemas.alert import (
    AlertRuleCreateRequest,
    AlertRuleResponse,
    AlertRuleUpdateRequest,
)
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/alerts/rules", tags=["alerts"])


@router.post(
    "",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new alert rule (Admin/Operator only)",
)
async def create_alert_rule(
    payload: AlertRuleCreateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> AlertRuleResponse:
    """Creates a new metric threshold alert rule."""
    # If scoped to a specific agent, verify agent exists
    if payload.agent_id is not None:
        agent_stmt = select(Agent).where(Agent.id == payload.agent_id)
        agent_res = await db.execute(agent_stmt)
        if agent_res.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scoped agent {payload.agent_id} does not exist",
            )

    rule = AlertRule(
        name=payload.name,
        metric_key=payload.metric_key,
        operator=payload.operator,
        threshold=payload.threshold,
        severity=payload.severity,
        evaluation_window_seconds=payload.evaluation_window_seconds,
        consecutive_breaches=payload.consecutive_breaches,
        cooldown_seconds=payload.cooldown_seconds,
        dimension_filter=payload.dimension_filter,
        dimension_aggregation=payload.dimension_aggregation,
        agent_id=payload.agent_id,
        enabled=payload.enabled,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    await record_audit_log(
        db,
        action="ALERT_RULE_CREATED",
        target_type="alert_rule",
        target_id=str(rule.id),
        actor_user_id=current_user.id,
        metadata={"name": rule.name, "metric_key": rule.metric_key},
    )

    return AlertRuleResponse.model_validate(rule)


@router.get(
    "",
    response_model=list[AlertRuleResponse],
    summary="List all alert rules with optional filters",
)
async def list_alert_rules(
    enabled: bool | None = Query(None, description="Filter by enabled state"),
    agent_id: uuid.UUID | None = Query(None, description="Filter by agent UUID"),
    severity: AlertSeverity | None = Query(None, description="Filter by severity"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AlertRuleResponse]:
    """Lists configured alert rules."""
    stmt = select(AlertRule).order_by(AlertRule.created_at.desc())

    if enabled is not None:
        stmt = stmt.where(AlertRule.enabled == enabled)
    if agent_id is not None:
        stmt = stmt.where(AlertRule.agent_id == agent_id)
    if severity is not None:
        stmt = stmt.where(AlertRule.severity == severity)

    result = await db.execute(stmt)
    rules = result.scalars().all()
    return [AlertRuleResponse.model_validate(r) for r in rules]


@router.get(
    "/{rule_id}",
    response_model=AlertRuleResponse,
    summary="Retrieve single alert rule by ID",
)
async def get_alert_rule(
    rule_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertRuleResponse:
    """Retrieves an alert rule by its UUID."""
    stmt = select(AlertRule).where(AlertRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )

    return AlertRuleResponse.model_validate(rule)


@router.patch(
    "/{rule_id}",
    response_model=AlertRuleResponse,
    summary="Update alert rule (Admin/Operator only)",
)
async def update_alert_rule(
    rule_id: uuid.UUID,
    payload: AlertRuleUpdateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> AlertRuleResponse:
    """Updates properties of an existing alert rule."""
    stmt = select(AlertRule).where(AlertRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(rule, field, val)

    await db.commit()
    await db.refresh(rule)

    await record_audit_log(
        db,
        action="ALERT_RULE_UPDATED",
        target_type="alert_rule",
        target_id=str(rule.id),
        actor_user_id=current_user.id,
        metadata={"updated_fields": list(update_data.keys())},
    )

    return AlertRuleResponse.model_validate(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete alert rule (Admin/Operator only)",
)
async def delete_alert_rule(
    rule_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Deletes an alert rule."""
    stmt = select(AlertRule).where(AlertRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )

    await db.delete(rule)
    await db.commit()

    await record_audit_log(
        db,
        action="ALERT_RULE_DELETED",
        target_type="alert_rule",
        target_id=str(rule_id),
        actor_user_id=current_user.id,
        metadata={"deleted_name": rule.name},
    )

    return {"message": "Alert rule deleted successfully"}
