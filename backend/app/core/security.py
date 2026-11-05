"""
OpsPulse Backend — Security & Cryptography Utilities

Provides:
- Native Bcrypt hashing and verification for user passwords and agent credentials.
- Cryptographically secure secret token generation.
- JWT encoding, decoding, and validation for user sessions.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_secret(secret: str) -> str:
    """Generate a bcrypt hash of a password or agent secret (native bcrypt, 12 rounds default)."""
    secret_bytes = secret.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(secret_bytes, salt).decode("utf-8")


def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
    """Verify that a plaintext secret matches its bcrypt hash."""
    try:
        secret_bytes = plain_secret.encode("utf-8")[:72]
        return bcrypt.checkpw(secret_bytes, hashed_secret.encode("utf-8"))
    except Exception:
        return False


def generate_agent_secret() -> str:
    """Generate a high-entropy 64-character hex secret token (32 random bytes)."""
    return secrets.token_hex(32)


def create_access_token(
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived access JWT (default 15 minutes)."""
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token. Returns claims dict or None if invalid/expired."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None
