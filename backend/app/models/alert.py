"""
OpsPulse Backend — Alert Rule Database Model

Defines alert rule criteria, thresholds, severity, and evaluation parameters
per spec Section 12 and Section 17.4.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AlertSeverity(str, enum.Enum):
    """Alert severity classification."""

    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertOperator(str, enum.Enum):
    """Comparison operator for metric evaluation."""

    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="


class DimensionAggregation(str, enum.Enum):
    """Aggregation mode when evaluating per-dimension metrics without a specific filter."""

    EACH = "EACH"
    MAX = "MAX"


class AlertRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Configurable alert rule stored in PostgreSQL."""

    __tablename__ = "alert_rules"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    metric_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    operator: Mapped[AlertOperator] = mapped_column(
        Enum(AlertOperator, name="alert_operator", native_enum=True),
        nullable=False,
    )
    threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity", native_enum=True),
        default=AlertSeverity.WARNING,
        nullable=False,
        index=True,
    )
    evaluation_window_seconds: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
    )
    consecutive_breaches: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    cooldown_seconds: Mapped[int] = mapped_column(
        Integer,
        default=300,
        nullable=False,
    )
    dimension_filter: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    dimension_aggregation: Mapped[DimensionAggregation | None] = mapped_column(
        Enum(DimensionAggregation, name="dimension_aggregation", native_enum=True),
        default=DimensionAggregation.EACH,
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AlertRule id={self.id} name={self.name} metric={self.metric_key} {self.operator.value} {self.threshold}>"

