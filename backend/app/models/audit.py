"""
OpsPulse Backend — Audit Log Database Model

Adheres strictly to spec Section 17.10:
- Primary key UUID
- actor_user_id (nullable UUID)
- actor_agent_id (nullable UUID)
- action (e.g. USER_LOGIN, AGENT_PROVISIONED, AGENT_REVOKED)
- target_type, target_id
- metadata (JSONB; safe values only, never secrets)
- created_at (UTC datetime)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """Audit trail entry recording security-relevant actions."""

    __tablename__ = "audit_logs"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    actor_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    target_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} target={self.target_type}:{self.target_id}>"
