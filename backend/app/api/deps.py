"""
OpsPulse Backend — API Dependencies

Provides:
- User authentication and RBAC authorization (JWT from cookie or Authorization header).
- Agent authentication (X-Agent-ID and X-Agent-Secret validated against bcrypt hash).
- Database session injection.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, verify_secret
from app.database.session import get_db
from app.models.agent import Agent
from app.models.user import User, UserRole


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extracts access token from HttpOnly cookie or Authorization Bearer header,
    decodes JWT, and returns the active User.
    """
    token: str | None = request.cookies.get("access_token")

    # Fallback to Authorization: Bearer <token>
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token subject",
        ) from err

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return user


def require_role(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Factory dependency enforcing RBAC role permissions."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation",
            )
        return current_user

    return role_checker


async def get_current_agent(
    x_agent_id: str | None = Header(None, alias="X-Agent-ID"),
    x_agent_secret: str | None = Header(None, alias="X-Agent-Secret"),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """
    Validates agent credentials from headers against the bcrypt hash in PostgreSQL.
    Rejects revoked or unregistered agents.
    """
    if not x_agent_id or not x_agent_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing agent authentication headers (X-Agent-ID, X-Agent-Secret)",
        )

    try:
        agent_uuid = uuid.UUID(x_agent_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent ID format",
        ) from err

    stmt = select(Agent).where(Agent.id == agent_uuid)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unregistered agent identity",
        )

    if agent.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent credential has been revoked",
        )

    if not verify_secret(x_agent_secret, agent.credential_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent secret",
        )

    return agent
