"""
OpsPulse Backend — Authentication Endpoints

Provides:
- POST /auth/login    — issues HttpOnly SameSite=Strict cookie containing JWT
- POST /auth/logout   — clears cookie and terminates session
- GET  /auth/me       — returns current authenticated user profile
- POST /auth/register — Admin-only endpoint to create users and assign roles
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.security import create_access_token, hash_secret, verify_secret
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, UserRegisterRequest, UserResponse
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserResponse, summary="Log in with email and password")
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Authenticates user credentials and issues an HttpOnly session cookie."""
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_secret(payload.password, user.password_hash):
        await record_audit_log(
            db,
            action="LOGIN_FAILED",
            target_type="user",
            target_id=payload.email,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
    )

    # Set secure HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="strict",
        secure=False,  # Set to True in production with HTTPS
        max_age=15 * 60,
    )

    await record_audit_log(
        db,
        action="USER_LOGIN",
        target_type="user",
        target_id=str(user.id),
        actor_user_id=user.id,
    )

    return UserResponse.model_validate(user)


@router.post("/logout", summary="Log out of current session")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Clears session cookie and records audit entry."""
    response.delete_cookie(key="access_token", samesite="strict")
    await record_audit_log(
        db,
        action="USER_LOGOUT",
        target_type="user",
        target_id=str(current_user.id),
        actor_user_id=current_user.id,
    )
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Returns profile for currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin-only: register a new user",
)
async def register_user(
    payload: UserRegisterRequest,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Admin-only endpoint to create user accounts with specified roles."""
    # Check if email is already taken
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    new_user = User(
        email=payload.email,
        password_hash=hash_secret(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await record_audit_log(
        db,
        action="USER_CREATED",
        target_type="user",
        target_id=str(new_user.id),
        actor_user_id=current_admin.id,
        metadata={"email": new_user.email, "role": new_user.role.value},
    )

    return UserResponse.model_validate(new_user)
