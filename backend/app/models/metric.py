"""
OpsPulse Backend — Metric Database Models

Stores raw time-series telemetry records and downsampled metric aggregates
per spec Section 11, Section 17.7, and Section 17.8.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class MetricRecord(Base, UUIDPrimaryKeyMixin):
    """
    Core point-in-time telemetry snapshot for an agent.
    Captures host-level CPU and RAM utilization.
    """

    __tablename__ = "metric_records"
    __table_args__ = (Index("ix_metric_records_agent_timestamp", "agent_id", "timestamp"),)

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    cpu_usage_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    memory_usage_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Relationships to partition and interface details
    disks: Mapped[list[MetricDisk]] = relationship(
        "MetricDisk",
        back_populates="record",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    networks: Mapped[list[MetricNetwork]] = relationship(
        "MetricNetwork",
        back_populates="record",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<MetricRecord id={self.id} agent_id={self.agent_id} time={self.timestamp}>"


class MetricDisk(Base, UUIDPrimaryKeyMixin):
    """Telemetry record for an individual mounted filesystem."""

    __tablename__ = "metric_disks"

    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mount_point: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    device: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    fstype: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    total_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    used_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    free_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    usage_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    record: Mapped[MetricRecord] = relationship(
        "MetricRecord",
        back_populates="disks",
    )


class MetricNetwork(Base, UUIDPrimaryKeyMixin):
    """Telemetry record for an individual network interface."""

    __tablename__ = "metric_networks"

    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interface_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    bytes_sent: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    bytes_recv: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    bytes_sent_per_sec: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    bytes_recv_per_sec: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    packets_sent_per_sec: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    packets_recv_per_sec: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    record: Mapped[MetricRecord] = relationship(
        "MetricRecord",
        back_populates="networks",
    )


class MetricAggregate(Base, UUIDPrimaryKeyMixin):
    """
    Downsampled metric bucket per spec Section 17.8.
    Retained 30 days by default for performant long-range queries.
    """

    __tablename__ = "metric_aggregates"
    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "metric_key",
            "dimension",
            "bucket_start",
            "bucket_size",
            name="uq_metric_aggregates_bucket",
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "ix_metric_aggregates_query",
            "agent_id",
            "metric_key",
            "bucket_start",
        ),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    dimension: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    bucket_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    bucket_size: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    min_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    max_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    avg_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    sample_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MetricAggregate agent_id={self.agent_id} key={self.metric_key} bucket={self.bucket_start}>"
