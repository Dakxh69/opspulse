"""
OpsPulse Backend — Incident Management Pydantic Schemas

Validates request payloads and formats responses for incidents and timeline events
per spec Section 13 and Section 18.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.alert import AlertSeverity
from app.models.incident import IncidentEventType, IncidentStatus


class IncidentEventResponse(BaseModel):
    """Timeline event or operator note on an incident."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    event_type: IncidentEventType
    message: str
    actor_user_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime


class IncidentResponse(BaseModel):
    """Detailed representation of an incident."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    rule_id: uuid.UUID | None = None
    dimension: str | None = None
    title: str
    description: str
    severity: AlertSeverity
    status: IncidentStatus
    first_detected_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None = None
    acknowledged_by_user_id: uuid.UUID | None = None
    resolved_by_user_id: uuid.UUID | None = None
    events: list[IncidentEventResponse] = Field(default_factory=list)


class IncidentListResponse(BaseModel):
    """Paginated list of incidents."""

    items: list[IncidentResponse]
    total: int
    page: int
    limit: int


class IncidentNoteRequest(BaseModel):
    """Payload to append an investigation note to an incident."""

    message: str = Field(min_length=1, max_length=2000, description="Investigation note message")


class IncidentActionRequest(BaseModel):
    """Optional payload when acknowledging, resolving, or reopening an incident."""

    message: str | None = Field(default=None, max_length=2000, description="Optional explanation note")
