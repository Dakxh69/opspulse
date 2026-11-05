"""
OpsPulse Backend — API v1 Router

Aggregates all v1 endpoint routers into a single router.
Registered in main.py with the /api/v1 prefix.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()

# Health endpoints — always first, no auth required
api_router.include_router(health.router, tags=["health"])
