"""
OpsPulse Backend — Realtime WebSocket API Endpoint

Accepts authenticated WebSocket connections using query parameter `token` or session cookies
per spec Section 15 and DEC-008.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_access_token
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    """
    Authenticated WebSocket connection.
    Authenticates token from query param ?token=<jwt> or cookie 'access_token'.
    """
    auth_token = token or websocket.cookies.get("access_token")

    if not auth_token:
        logger.warning("WebSocket connection rejected: missing access token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_access_token(auth_token)
    if payload is None or "sub" not in payload:
        logger.warning("WebSocket connection rejected: invalid or expired access token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect(websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "event": "CONNECTED",
                "data": {"user_id": payload["sub"], "role": payload.get("role")},
            }
        )

        # Keep connection alive while listening for client messages (e.g. ping/pong)
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.error(f"WebSocket unexpected error: {exc}")
        ws_manager.disconnect(websocket)
