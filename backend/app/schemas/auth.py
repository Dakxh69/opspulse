"""
OpsPulse Backend — Authentication Schemas
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    """User login credential payload."""

    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    password: str = Field(..., min_length=1)


class UserRegisterRequest(BaseModel):
    """Admin-only user creation payload."""

    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.VIEWER


class UserResponse(BaseModel):
    """Public user profile response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
