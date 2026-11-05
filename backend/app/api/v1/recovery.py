"""
OpsPulse Backend — Recovery Policy & Execution Endpoints

Provides allowlisted remediation configuration, manual approvals, dry-run simulations,
and execution history auditing per spec Section 16, Section 17.7, and Section 18.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.database.session import get_db
from app.models.agent import Agent
from app.models.recovery import ExecutionStatus, RecoveryExecution, RecoveryPolicy
from app.models.user import User, UserRole
from app.schemas.recovery import (
    RecoveryExecuteRequest,
    RecoveryExecutionResponse,
    RecoveryPolicyCreateRequest,
    RecoveryPolicyResponse,
    RecoveryPolicyUpdateRequest,
)
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/recovery", tags=["recovery"])


@router.post(
    "/policies",
    response_model=RecoveryPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a recovery remediation policy (Admin only)",
)
async def create_recovery_policy(
    payload: RecoveryPolicyCreateRequest,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RecoveryPolicy:
    """Configures an allowlisted remediation policy."""
    policy = RecoveryPolicy(
        id=uuid.uuid4(),
        name=payload.name,
        rule_id=payload.rule_id,
        action_type=payload.action_type,
        target=payload.target,
        requires_approval=payload.requires_approval,
        enabled=payload.enabled,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    await record_audit_log(
        session=db,
        action="RECOVERY_POLICY_CREATED",
        target_type="recovery_policy",
        target_id=str(policy.id),
        actor_user_id=current_admin.id,
        metadata={
            "name": policy.name,
            "action_type": policy.action_type.value,
            "target": policy.target,
        },
    )

    return policy


@router.get(
    "/policies",
    response_model=list[RecoveryPolicyResponse],
    summary="List recovery policies (Admin and Operator)",
)
async def list_recovery_policies(
    enabled_only: bool = Query(False),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> list[RecoveryPolicy]:
    """Lists configured remediation policies."""
    stmt = select(RecoveryPolicy).order_by(RecoveryPolicy.created_at.desc())
    if enabled_only:
        stmt = stmt.where(RecoveryPolicy.enabled.is_(True))
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.patch(
    "/policies/{policy_id}",
    response_model=RecoveryPolicyResponse,
    summary="Update a recovery policy (Admin only)",
)
async def update_recovery_policy(
    policy_id: uuid.UUID,
    payload: RecoveryPolicyUpdateRequest,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RecoveryPolicy:
    """Updates configuration for an allowlisted policy."""
    policy = await db.get(RecoveryPolicy, policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery policy '{policy_id}' not found",
        )

    if payload.name is not None:
        policy.name = payload.name
    if payload.action_type is not None:
        policy.action_type = payload.action_type
    if payload.target is not None:
        policy.target = payload.target
    if payload.requires_approval is not None:
        policy.requires_approval = payload.requires_approval
    if payload.enabled is not None:
        policy.enabled = payload.enabled

    await db.commit()
    await db.refresh(policy)

    await record_audit_log(
        session=db,
        action="RECOVERY_POLICY_UPDATED",
        target_type="recovery_policy",
        target_id=str(policy.id),
        actor_user_id=current_admin.id,
        metadata={"name": policy.name},
    )

    return policy


@router.post(
    "/{policy_id}/execute",
    response_model=RecoveryExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request recovery execution (Admin and Operator)",
)
async def execute_recovery_policy(
    policy_id: uuid.UUID,
    payload: RecoveryExecuteRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> RecoveryExecution:
    """
    Submits a remediation execution request.
    Supports dry-run simulation mode and enforces approval requirements.
    """
    policy = await db.get(RecoveryPolicy, policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery policy '{policy_id}' not found",
        )

    if not policy.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot execute disabled recovery policy",
        )

    agent = await db.get(Agent, payload.target_agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target agent '{payload.target_agent_id}' not found",
        )

    now = datetime.now(UTC)

    if payload.dry_run:
        # Dry-run: simulate outcome safely without host action
        execution = RecoveryExecution(
            id=uuid.uuid4(),
            policy_id=policy.id,
            incident_id=payload.incident_id,
            target_agent_id=agent.id,
            requested_by_user_id=current_user.id,
            approved_by_user_id=current_user.id,
            status=ExecutionStatus.SUCCEEDED,
            dry_run=True,
            started_at=now,
            completed_at=now,
            output_summary=(
                f"[DRY-RUN] Simulated {policy.action_type.value} on target '{policy.target}' "
                f"for agent '{agent.hostname}'. No system state modified."
            ),
            created_at=now,
        )
    else:
        # Live execution: check approval rules
        initial_status = (
            ExecutionStatus.PENDING_APPROVAL
            if policy.requires_approval
            else ExecutionStatus.APPROVED
        )
        execution = RecoveryExecution(
            id=uuid.uuid4(),
            policy_id=policy.id,
            incident_id=payload.incident_id,
            target_agent_id=agent.id,
            requested_by_user_id=current_user.id,
            status=initial_status,
            dry_run=False,
            output_summary=(
                f"Queued {policy.action_type.value} on target '{policy.target}' "
                f"(status: {initial_status.value})"
            ),
            created_at=now,
        )

    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    await record_audit_log(
        session=db,
        action="RECOVERY_EXECUTION_REQUESTED",
        target_type="recovery_execution",
        target_id=str(execution.id),
        actor_user_id=current_user.id,
        metadata={
            "policy_name": policy.name,
            "target": policy.target,
            "dry_run": payload.dry_run,
            "status": execution.status.value,
        },
    )

    return execution


@router.post(
    "/executions/{execution_id}/approve",
    response_model=RecoveryExecutionResponse,
    summary="Approve a pending recovery execution (Admin only)",
)
async def approve_recovery_execution(
    execution_id: uuid.UUID,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RecoveryExecution:
    """Approves a PENDING_APPROVAL remediation request."""
    execution = await db.get(RecoveryExecution, execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution request '{execution_id}' not found",
        )

    if execution.status != ExecutionStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve execution in status '{execution.status.value}'",
        )

    execution.status = ExecutionStatus.APPROVED
    execution.approved_by_user_id = current_admin.id
    await db.commit()
    await db.refresh(execution)

    await record_audit_log(
        session=db,
        action="RECOVERY_EXECUTION_APPROVED",
        target_type="recovery_execution",
        target_id=str(execution.id),
        actor_user_id=current_admin.id,
    )

    return execution


@router.get(
    "/executions",
    response_model=list[RecoveryExecutionResponse],
    summary="List recovery executions (Admin and Operator)",
)
async def list_recovery_executions(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> list[RecoveryExecution]:
    """Retrieves chronological remediation execution history."""
    stmt = select(RecoveryExecution).order_by(RecoveryExecution.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
