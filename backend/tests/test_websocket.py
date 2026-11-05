"""
OpsPulse Backend — Realtime WebSocket Tests (Day 22)

Verifies:
- Authenticated connection with valid JWT
- Rejection of unauthenticated connection (missing or invalid token)
- Two-way communication (ping/pong)
"""

from __future__ import annotations

import uuid
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token, hash_secret
from app.main import app
from app.models.user import User, UserRole
from app.database.session import SyncSessionLocal


def test_websocket_authentication_success() -> None:
    """Verifies that a client with a valid JWT token successfully establishes a WebSocket session."""
    with SyncSessionLocal() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"ws_user_{uuid.uuid4().hex[:6]}@opspulse.local",
            password_hash=hash_secret("Password123!"),
            role=UserRole.OPERATOR,
            is_active=True,
        )
        session.add(user)
        session.commit()
        token = create_access_token(subject=str(user.id), role=user.role.value)

    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
        data = ws.receive_json()
        assert data["event"] == "CONNECTED"
        assert data["data"]["user_id"] == str(user.id)

        # Test ping/pong
        ws.send_text("ping")
        reply = ws.receive_text()
        assert reply == "pong"


def test_websocket_rejection_without_token() -> None:
    """Verifies that an unauthenticated WebSocket connection is immediately closed with policy violation."""
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws"):
            pass
    assert exc_info.value.code == 1008

