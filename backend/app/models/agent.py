"""
OpsPulse Backend — Agent Database Model

Represents monitored Linux hosts running an OpsPulse monitoring agent.
Adheres strictly to spec Section 17.2.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AgentStatus(str, enum.Enum):
    """Operational health state of a monitored host agent."""

    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


class Agent(Base, UUIDPrimaryKeyMixin):
    """Monitored agent registration entity."""

    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    hostname: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    os_type: Mapped[str] = mapped_column(
        String(100),
        default="Linux",
        nullable=False,
    )
    agent_version: Mapped[str] = mapped_column(
        String(50),
        default="0.1.0",
        nullable=False,
    )
    credential_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status", native_enum=True),
        default=AgentStatus.ONLINE,
        nullable=False,
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name} status={self.status}>"

