"""
OpsPulse Backend — Incident Management API Endpoints

Provides lifecycle transition endpoints, detail views, filtering, note addition,
and chronological event timelines per spec Section 13 and Section 18.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.database.session import get_db
from app.models.alert import AlertSeverity
from app.models.incident import (
    Incident,
    IncidentEvent,
    IncidentEventType,
    IncidentStatus,
)
from app.models.user import User, UserRole
from app.schemas.incident import (
    IncidentActionRequest,
    IncidentEventResponse,
    IncidentListResponse,
    IncidentNoteRequest,
    IncidentResponse,
)
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get(
    "",
    response_model=IncidentListResponse,
    summary="List incidents with filtering and pagination",
)
async def list_incidents(
    status_filter: IncidentStatus | None = Query(None, alias="status"),
    severity: AlertSeverity | None = Query(None),
    agent_id: uuid.UUID | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncidentListResponse:
    """Lists incidents ordered by latest activity."""
    stmt = select(Incident).options(selectinload(Incident.events))

    if status_filter is not None:
        stmt = stmt.where(Incident.status == status_filter)
    if severity is not None:
        stmt = stmt.where(Incident.severity == severity)
    if agent_id is not None:
        stmt = stmt.where(Incident.agent_id == agent_id)
    if start_time is not None:
        stmt = stmt.where(Incident.first_detected_at >= start_time)
    if end_time is not None:
        stmt = stmt.where(Incident.first_detected_at <= end_time)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Paginate
    offset = (page - 1) * limit
    paginated_stmt = stmt.order_by(Incident.last_seen_at.desc()).offset(offset).limit(limit)
    res = await db.execute(paginated_stmt)
    items = list(res.scalars().all())

    return IncidentListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident details and event history",
)
async def get_incident(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Incident:
    """Retrieves single incident with chronological events."""
    stmt = select(Incident).options(selectinload(Incident.events)).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    incident = res.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )
    return incident


@router.post(
    "/{incident_id}/acknowledge",
    response_model=IncidentResponse,
    summary="Acknowledge an incident (Admin/Operator only)",
)
async def acknowledge_incident(
    incident_id: uuid.UUID,
    payload: IncidentActionRequest | None = None,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> Incident:
    """Transitions an OPEN or INVESTIGATING incident to ACKNOWLEDGED."""
    stmt = select(Incident).options(selectinload(Incident.events)).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    incident = res.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )

    if incident.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot acknowledge incident in status '{incident.status.value}'",
        )

    now = datetime.now(UTC)
    incident.status = IncidentStatus.ACKNOWLEDGED
    incident.acknowledged_by_user_id = current_user.id
    incident.last_seen_at = now

    msg = (
        payload.message
        if payload and payload.message
        else f"Incident acknowledged by {current_user.email}"
    )
    event = IncidentEvent(
        id=uuid.uuid4(),
        incident_id=incident.id,
        event_type=IncidentEventType.ACKNOWLEDGED,
        message=msg,
        actor_user_id=current_user.id,
        metadata_={"acknowledged_by": current_user.email},
        created_at=now,
    )
    incident.events.append(event)
    await db.commit()
    await db.refresh(incident)

    await record_audit_log(
        session=db,
        action="INCIDENT_ACKNOWLEDGE",
        target_type="incident",
        target_id=str(incident.id),
        actor_user_id=current_user.id,
        metadata={"title": incident.title, "severity": incident.severity.value},
    )

    return incident


@router.post(
    "/{incident_id}/resolve",
    response_model=IncidentResponse,
    summary="Resolve an incident (Admin/Operator only)",
)
async def resolve_incident(
    incident_id: uuid.UUID,
    payload: IncidentActionRequest | None = None,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> Incident:
    """Transitions an active incident to RESOLVED."""
    stmt = select(Incident).options(selectinload(Incident.events)).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    incident = res.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )

    if incident.status == IncidentStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident is already CLOSED",
        )

    now = datetime.now(UTC)
    incident.status = IncidentStatus.RESOLVED
    incident.resolved_by_user_id = current_user.id
    incident.resolved_at = now
    incident.last_seen_at = now

    msg = (
        payload.message
        if payload and payload.message
        else f"Incident resolved by {current_user.email}"
    )
    event = IncidentEvent(
        id=uuid.uuid4(),
        incident_id=incident.id,
        event_type=IncidentEventType.RESOLVED,
        message=msg,
        actor_user_id=current_user.id,
        metadata_={"resolved_by": current_user.email},
        created_at=now,
    )
    incident.events.append(event)
    await db.commit()
    await db.refresh(incident)

    await record_audit_log(
        session=db,
        action="INCIDENT_RESOLVE",
        target_type="incident",
        target_id=str(incident.id),
        actor_user_id=current_user.id,
        metadata={"title": incident.title, "resolved_at": now.isoformat()},
    )

    return incident


@router.post(
    "/{incident_id}/reopen",
    response_model=IncidentResponse,
    summary="Reopen a resolved or closed incident (Admin/Operator only)",
)
async def reopen_incident(
    incident_id: uuid.UUID,
    payload: IncidentActionRequest | None = None,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> Incident:
    """Transitions a RESOLVED or CLOSED incident back to OPEN."""
    stmt = select(Incident).options(selectinload(Incident.events)).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    incident = res.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )

    if incident.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reopen incident in status '{incident.status.value}'; it is already active",
        )

    now = datetime.now(UTC)
    incident.status = IncidentStatus.OPEN
    incident.resolved_at = None
    incident.resolved_by_user_id = None
    incident.last_seen_at = now

    msg = (
        payload.message
        if payload and payload.message
        else f"Incident reopened by {current_user.email}"
    )
    event = IncidentEvent(
        id=uuid.uuid4(),
        incident_id=incident.id,
        event_type=IncidentEventType.REOPENED,
        message=msg,
        actor_user_id=current_user.id,
        metadata_={"reopened_by": current_user.email},
        created_at=now,
    )
    incident.events.append(event)
    await db.commit()
    await db.refresh(incident)

    await record_audit_log(
        session=db,
        action="INCIDENT_REOPEN",
        target_type="incident",
        target_id=str(incident.id),
        actor_user_id=current_user.id,
        metadata={"title": incident.title},
    )

    return incident


@router.post(
    "/{incident_id}/notes",
    response_model=IncidentEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an investigation note to an incident (Admin/Operator only)",
)
async def add_incident_note(
    incident_id: uuid.UUID,
    payload: IncidentNoteRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> IncidentEvent:
    """Adds a note to the incident timeline."""
    incident = await db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )

    now = datetime.now(UTC)
    event = IncidentEvent(
        id=uuid.uuid4(),
        incident_id=incident.id,
        event_type=IncidentEventType.NOTE_ADDED,
        message=payload.message,
        actor_user_id=current_user.id,
        metadata_={"author": current_user.email},
        created_at=now,
    )
    db.add(event)
    incident.last_seen_at = now
    await db.commit()
    await db.refresh(event)

    return event


@router.get(
    "/{incident_id}/events",
    response_model=list[IncidentEventResponse],
    summary="Get chronological timeline events for an incident",
)
async def get_incident_events(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[IncidentEvent]:
    """Retrieves all timeline events ordered chronologically."""
    incident = await db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )

    stmt = (
        select(IncidentEvent)
        .where(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.created_at.asc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())
