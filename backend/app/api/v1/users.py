"""
OpsPulse Backend — User Management Endpoints (Admin Only)

Provides:
- GET   /users     — list all registered users
- GET   /users/{id} — get user details
- PATCH /users/{id} — update user role and active status
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/users", tags=["users"])


class UserUpdateRequest(BaseModel):
    """Payload to update user role or active status."""

    role: UserRole | None = None
    is_active: bool | None = None


@router.get("", response_model=list[UserResponse], summary="Admin-only: list all users")
async def list_users(
    _: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """Lists all user accounts."""
    stmt = select(User).order_by(User.created_at.asc())
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse, summary="Admin-only: get user details")
async def get_user(
    user_id: uuid.UUID,
    _: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Retrieves a single user by ID."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse, summary="Admin-only: update user")
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Modifies a user's role or deactivates an account."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent admin from deactivating themselves
    if user.id == current_admin.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate own admin account",
        )

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)

    await record_audit_log(
        db,
        action="USER_MODIFIED",
        target_type="user",
        target_id=str(user.id),
        actor_user_id=current_admin.id,
        metadata={"role": user.role.value, "is_active": user.is_active},
    )

    return UserResponse.model_validate(user)
