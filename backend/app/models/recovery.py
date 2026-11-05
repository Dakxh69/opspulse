"""
OpsPulse Backend — Recovery Policy & Execution Database Models

Models for allowlisted operational remediations per spec Section 16 and Section 17.7.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ActionType(str, enum.Enum):
    """Allowlisted remediation action types."""

    SERVICE_RESTART = "SERVICE_RESTART"
    CONTAINER_RESTART = "CONTAINER_RESTART"
    CLEANUP_SCRIPT = "CLEANUP_SCRIPT"
    DIAGNOSTIC = "DIAGNOSTIC"


class ExecutionStatus(str, enum.Enum):
    """Execution lifecycle status for recovery requests."""

    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class RecoveryPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Defines an allowable remediation action bound to an alert rule or target."""

    __tablename__ = "recovery_policies"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType, name="recovery_action_type", native_enum=True),
        nullable=False,
    )
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    executions: Mapped[list[RecoveryExecution]] = relationship(
        "RecoveryExecution",
        back_populates="policy",
        cascade="all, delete-orphan",
    )


class RecoveryExecution(Base, UUIDPrimaryKeyMixin):
    """Records an executed or pending remediation attempt."""

    __tablename__ = "recovery_executions"

    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recovery_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, name="recovery_execution_status", native_enum=True),
        default=ExecutionStatus.PENDING_APPROVAL,
        nullable=False,
        index=True,
    )
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    policy: Mapped[RecoveryPolicy] = relationship(
        "RecoveryPolicy",
        back_populates="executions",
    )
