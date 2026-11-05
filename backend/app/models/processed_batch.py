"""
OpsPulse Backend — Processed Batches Database Model

Tracks ingested metric batch delivery and processing status for worker idempotency
and deduplication per spec Section 17.9.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class BatchStatus(str, enum.Enum):
    """Processing state of an ingested metric batch."""

    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class ProcessedBatch(Base, UUIDPrimaryKeyMixin):
    """
    Idempotency and deduplication tracking record.
    Enforces uniqueness on (agent_id, batch_id).
    """

    __tablename__ = "processed_batches"
    __table_args__ = (
        UniqueConstraint("agent_id", "batch_id", name="uq_processed_batches_agent_batch"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus, name="batch_status", native_enum=True),
        default=BatchStatus.RECEIVED,
        nullable=False,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_summary: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<ProcessedBatch id={self.id} agent_id={self.agent_id} batch_id={self.batch_id} status={self.status}>"
