"""
OpsPulse Backend — Audit Schemas

Pydantic models for serializing audit logs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Serialized audit log entry."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None = None
    actor_agent_id: uuid.UUID | None = None
    action: str
    target_type: str
    target_id: str
    metadata: dict[str, Any] = Field(..., alias="metadata_")
    created_at: datetime


class AuditLogPageResponse(BaseModel):
    """Paginated list of audit logs."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
