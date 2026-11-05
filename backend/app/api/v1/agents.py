"""
OpsPulse Backend — Agent Management Endpoints

Provides:
- POST   /agents/register          — provision agent & return one-time secret
- GET    /agents                   — list monitored agents
- GET    /agents/{id}              — get agent details
- PATCH  /agents/{id}              — update agent metadata
- DELETE /agents/{id}              — revoke agent credential & deactivate
- POST   /agents/{id}/rotate-credential — rotate credential & return one-time new secret
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_agent, get_current_user, require_role
from app.core.security import generate_agent_secret, hash_secret
from app.database.session import get_db
from app.models.agent import Agent, AgentStatus
from app.models.user import User, UserRole
from app.schemas.agent import (
    AgentProvisionResponse,
    AgentRegisterRequest,
    AgentResponse,
    AgentRotateSecretResponse,
    AgentUpdateRequest,
)
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post(
    "/register",
    response_model=AgentProvisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a new agent (returns secret once)",
)
async def register_agent(
    payload: AgentRegisterRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> AgentProvisionResponse:
    """Provisions a new agent and returns the plaintext secret key once."""
    plaintext_secret = generate_agent_secret()
    secret_hash = hash_secret(plaintext_secret)

    agent = Agent(
        name=payload.name,
        hostname=payload.hostname,
        os_type=payload.os_type,
        agent_version=payload.agent_version,
        credential_hash=secret_hash,
        status=AgentStatus.ONLINE,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    await record_audit_log(
        db,
        action="AGENT_PROVISIONED",
        target_type="agent",
        target_id=str(agent.id),
        actor_user_id=current_user.id,
        metadata={"name": agent.name, "hostname": agent.hostname},
    )

    return AgentProvisionResponse(
        agent_id=agent.id,
        name=agent.name,
        hostname=agent.hostname,
        agent_secret=plaintext_secret,
    )


@router.get("", response_model=list[AgentResponse], summary="List all monitored agents")
async def list_agents(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentResponse]:
    """Returns a list of all registered agents (excluding credential hashes)."""
    stmt = select(Agent).order_by(Agent.created_at.desc())
    result = await db.execute(stmt)
    agents = result.scalars().all()
    return [AgentResponse.model_validate(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentResponse, summary="Get agent details")
async def get_agent(
    agent_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Retrieves agent metadata by ID."""
    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse, summary="Update agent metadata")
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Updates editable agent metadata (name, hostname)."""
    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if payload.name is not None:
        agent.name = payload.name
    if payload.hostname is not None:
        agent.hostname = payload.hostname

    await db.commit()
    await db.refresh(agent)

    await record_audit_log(
        db,
        action="AGENT_UPDATED",
        target_type="agent",
        target_id=str(agent.id),
        actor_user_id=current_user.id,
    )

    return AgentResponse.model_validate(agent)


@router.delete(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Revoke an agent credential",
)
async def revoke_agent(
    agent_id: uuid.UUID,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Revokes an agent's credential, marking it revoked and offline."""
    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    agent.revoked_at = datetime.now(UTC)
    agent.status = AgentStatus.OFFLINE
    await db.commit()
    await db.refresh(agent)

    await record_audit_log(
        db,
        action="AGENT_REVOKED",
        target_type="agent",
        target_id=str(agent.id),
        actor_user_id=current_admin.id,
    )

    return AgentResponse.model_validate(agent)


@router.post(
    "/{agent_id}/rotate-credential",
    response_model=AgentRotateSecretResponse,
    summary="Rotate agent credential",
)
async def rotate_agent_credential(
    agent_id: uuid.UUID,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AgentRotateSecretResponse:
    """Rotates an agent's credential, immediately invalidating the prior secret."""
    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    new_secret = generate_agent_secret()
    agent.credential_hash = hash_secret(new_secret)
    agent.revoked_at = None  # Re-enable if it was revoked
    await db.commit()

    await record_audit_log(
        db,
        action="AGENT_CREDENTIAL_ROTATED",
        target_type="agent",
        target_id=str(agent.id),
        actor_user_id=current_admin.id,
    )

    return AgentRotateSecretResponse(
        agent_id=agent.id,
        new_agent_secret=new_secret,
    )


@router.post(
    "/heartbeat",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Agent periodic liveness ping",
)
async def agent_heartbeat(
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Updates the agent's last_heartbeat timestamp and ensures status is ONLINE."""
    current_agent.last_heartbeat = datetime.now(UTC)
    current_agent.status = AgentStatus.ONLINE
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
