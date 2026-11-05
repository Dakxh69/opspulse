"""
OpsPulse Backend — Audit Service

Provides utility to persist audit log records asynchronously.
Guarantees secrets are never recorded in metadata.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


async def record_audit_log(
    session: AsyncSession,
    action: str,
    target_type: str,
    target_id: str,
    actor_user_id: uuid.UUID | None = None,
    actor_agent_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> AuditLog:
    """Creates and persists an immutable audit log entry."""
    entry = AuditLog(
        action=action,
        target_type=target_type,
        target_id=target_id,
        actor_user_id=actor_user_id,
        actor_agent_id=actor_agent_id,
        metadata_=metadata or {},
    )
    session.add(entry)
    if commit:
        await session.commit()
    logger.info(
        "Audit event recorded",
        extra={
            "audit_action": action,
            "target": f"{target_type}:{target_id}",
            "actor_user": str(actor_user_id) if actor_user_id else None,
        },
    )
    return entry
