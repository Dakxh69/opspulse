"""
OpsPulse Backend — Audit Log Endpoints (Admin Only)

Provides:
- GET /audit-logs — paginated list of security audit events with filtering.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.database.session import get_db
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.schemas.audit import AuditLogPageResponse, AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get(
    "",
    response_model=AuditLogPageResponse,
    summary="Admin-only: list and filter audit trail logs",
)
async def list_audit_logs(
    actor_id: uuid.UUID | None = Query(None, description="Filter by actor UUID"),
    action: str | None = Query(None, description="Filter by action name"),
    target_type: str | None = Query(None, description="Filter by target type"),
    target_id: str | None = Query(None, description="Filter by target ID"),
    start_time: datetime | None = Query(None, description="Earliest UTC created_at"),
    end_time: datetime | None = Query(None, description="Latest UTC created_at"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    _: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AuditLogPageResponse:
    """Retrieves paginated audit events with optional multi-attribute filters."""
    query = select(AuditLog)
    count_query = select(func.count()).select_from(AuditLog)

    conditions: list[Any] = []
    if actor_id:
        conditions.append(
            (AuditLog.actor_user_id == actor_id) | (AuditLog.actor_agent_id == actor_id)
        )
    if action:
        conditions.append(AuditLog.action == action)
    if target_type:
        conditions.append(AuditLog.target_type == target_type)
    if target_id:
        conditions.append(AuditLog.target_id == target_id)
    if start_time:
        conditions.append(AuditLog.created_at >= start_time)
    if end_time:
        conditions.append(AuditLog.created_at <= end_time)

    if conditions:
        for cond in conditions:
            query = query.where(cond)
            count_query = count_query.where(cond)

    total_res = await db.execute(count_query)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    return AuditLogPageResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
