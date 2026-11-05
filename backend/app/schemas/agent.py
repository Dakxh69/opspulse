"""
OpsPulse Backend — Agent Schemas
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.agent import AgentStatus


class AgentRegisterRequest(BaseModel):
    """Payload to register/provision a new agent."""

    name: str = Field(..., max_length=100)
    hostname: str = Field(..., max_length=255)
    os_type: str = Field(default="Linux", max_length=100)
    agent_version: str = Field(default="0.1.0", max_length=50)


class AgentProvisionResponse(BaseModel):
    """Response returned ONCE upon agent registration containing plaintext secret."""

    agent_id: uuid.UUID
    name: str
    hostname: str
    agent_secret: str
    message: str = "Record this secret token now. It will not be shown again."


class AgentRotateSecretResponse(BaseModel):
    """Response returned ONCE upon agent credential rotation."""

    agent_id: uuid.UUID
    new_agent_secret: str
    message: str = "Record this new secret token now. The previous secret is now invalidated."


class AgentResponse(BaseModel):
    """Public agent metadata schema (never exposes secret or credential hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    hostname: str
    os_type: str
    agent_version: str
    status: AgentStatus
    last_heartbeat: datetime | None = None
    created_at: datetime
    revoked_at: datetime | None = None


class AgentUpdateRequest(BaseModel):
    """Payload to update editable agent properties."""

    name: str | None = Field(None, max_length=100)
    hostname: str | None = Field(None, max_length=255)
