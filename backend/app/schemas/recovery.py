"""
OpsPulse Backend — Recovery Policy & Execution Schemas
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.recovery import ActionType, ExecutionStatus


class RecoveryPolicyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    rule_id: uuid.UUID | None = None
    action_type: ActionType
    target: str = Field(min_length=1, max_length=255)
    requires_approval: bool = True
    enabled: bool = True


class RecoveryPolicyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    rule_id: uuid.UUID | None = None
    action_type: ActionType | None = None
    target: str | None = Field(default=None, min_length=1, max_length=255)
    requires_approval: bool | None = None
    enabled: bool | None = None


class RecoveryPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    rule_id: uuid.UUID | None = None
    action_type: ActionType
    target: str
    requires_approval: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime


class RecoveryExecuteRequest(BaseModel):
    target_agent_id: uuid.UUID
    incident_id: uuid.UUID | None = None
    dry_run: bool = False


class RecoveryExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    policy_id: uuid.UUID
    incident_id: uuid.UUID | None = None
    target_agent_id: uuid.UUID
    requested_by_user_id: uuid.UUID | None = None
    approved_by_user_id: uuid.UUID | None = None
    status: ExecutionStatus
    dry_run: bool
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output_summary: str | None = None
    created_at: datetime
