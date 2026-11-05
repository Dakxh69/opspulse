"""
OpsPulse Backend — Database Integration Tests

Verifies:
- Asynchronous database ping (`check_database_health`).
- User ORM model insertion, querying, and uniqueness constraints.
- Agent ORM model insertion, querying, and status updates.
- AsyncSession lifecycle and transaction rollbacks.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import check_database_health
from app.models.agent import Agent, AgentStatus
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_database_health_check() -> None:
    """Verifies that check_database_health executes a successful ping against PostgreSQL."""
    is_healthy = await check_database_health()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_create_and_query_user(db_session: AsyncSession) -> None:
    """Verifies inserting and retrieving a User entity via AsyncSession."""
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    user = User(
        email=test_email,
        password_hash="mock_bcrypt_hash_for_testing",
        role=UserRole.OPERATOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    user_id = user.id
    assert user_id is not None
    assert user.role == UserRole.OPERATOR
    assert user.created_at is not None

    # Query to verify persistence
    stmt = select(User).where(User.id == user_id)
    result = await db_session.execute(stmt)
    retrieved_user = result.scalar_one_or_none()

    assert retrieved_user is not None
    assert retrieved_user.email == test_email
    assert retrieved_user.role == UserRole.OPERATOR

    # Clean up
    await db_session.delete(retrieved_user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_user_email_unique_constraint(db_session: AsyncSession) -> None:
    """Verifies that inserting a duplicate email raises IntegrityError."""
    duplicate_email = f"dup_{uuid.uuid4().hex[:8]}@example.com"

    user1 = User(
        email=duplicate_email,
        password_hash="hash1",
        role=UserRole.VIEWER,
    )
    db_session.add(user1)
    await db_session.commit()

    user2 = User(
        email=duplicate_email,
        password_hash="hash2",
        role=UserRole.ADMIN,
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # Clean up first user
    stmt = select(User).where(User.email == duplicate_email)
    result = await db_session.execute(stmt)
    user_to_delete = result.scalar_one_or_none()
    if user_to_delete:
        await db_session.delete(user_to_delete)
        await db_session.commit()


@pytest.mark.asyncio
async def test_create_and_update_agent(db_session: AsyncSession) -> None:
    """Verifies inserting, querying, and updating an Agent entity."""
    test_agent_name = f"agent-{uuid.uuid4().hex[:6]}"

    agent = Agent(
        name=test_agent_name,
        hostname="test-host.local",
        os_type="Linux",
        agent_version="0.1.0",
        credential_hash="mock_agent_secret_hash",
        status=AgentStatus.ONLINE,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    agent_id = agent.id
    assert agent_id is not None
    assert agent.status == AgentStatus.ONLINE

    # Update agent status
    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db_session.execute(stmt)
    agent_to_update = result.scalar_one_or_none()

    assert agent_to_update is not None
    agent_to_update.status = AgentStatus.DEGRADED
    await db_session.commit()

    # Verify updated status
    result = await db_session.execute(stmt)
    verified_agent = result.scalar_one_or_none()

    assert verified_agent is not None
    assert verified_agent.status == AgentStatus.DEGRADED

    # Clean up
    await db_session.delete(verified_agent)
    await db_session.commit()
