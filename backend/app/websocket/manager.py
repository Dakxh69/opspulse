"""
OpsPulse Backend — Realtime WebSocket Connection Manager

Manages active browser WebSocket connections and broadcasts incident & telemetry notifications
per spec Section 15 ("Realtime behavior").
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks active client WebSockets and broadcasts JSON events."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts and registers an incoming WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a disconnected WebSocket from the active list."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Active clients: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Broadcasts a structured event payload to all active clients."""
        payload = {"event": event_type, "data": data}
        dead_connections: list[WebSocket] = []

        for conn in self.active_connections:
            try:
                await conn.send_json(payload)
            except Exception as exc:
                logger.warning(f"Failed to send to client; marking dead: {exc}")
                dead_connections.append(conn)

        for dead in dead_connections:
            self.disconnect(dead)


# Global singleton manager
ws_manager = ConnectionManager()
