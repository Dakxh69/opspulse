"""
OpsPulse Backend — Alert Rule Schemas

Validation and serialization schemas for alert rule management (Day 12).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.alert import (
    AlertOperator,
    AlertSeverity,
    DimensionAggregation,
)


class AlertRuleCreateRequest(BaseModel):
    """Payload to create a new threshold alert rule."""

    name: str = Field(..., min_length=1, max_length=200)
    metric_key: str = Field(..., min_length=1, max_length=100)
    operator: AlertOperator
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING
    evaluation_window_seconds: int = Field(60, ge=10, le=86400)
    consecutive_breaches: int = Field(1, ge=1, le=100)
    cooldown_seconds: int = Field(300, ge=0, le=86400)
    dimension_filter: str | None = None
    dimension_aggregation: DimensionAggregation | None = DimensionAggregation.EACH
    agent_id: uuid.UUID | None = None
    enabled: bool = True


class AlertRuleUpdateRequest(BaseModel):
    """Payload to modify existing alert rule properties."""

    name: str | None = Field(None, min_length=1, max_length=200)
    threshold: float | None = None
    operator: AlertOperator | None = None
    severity: AlertSeverity | None = None
    evaluation_window_seconds: int | None = Field(None, ge=10, le=86400)
    consecutive_breaches: int | None = Field(None, ge=1, le=100)
    cooldown_seconds: int | None = Field(None, ge=0, le=86400)
    dimension_filter: str | None = None
    dimension_aggregation: DimensionAggregation | None = None
    enabled: bool | None = None


class AlertRuleResponse(BaseModel):
    """Public serialized alert rule schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    metric_key: str
    operator: AlertOperator
    threshold: float
    severity: AlertSeverity
    evaluation_window_seconds: int
    consecutive_breaches: int
    cooldown_seconds: int
    dimension_filter: str | None = None
    dimension_aggregation: DimensionAggregation | None = None
    agent_id: uuid.UUID | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime

