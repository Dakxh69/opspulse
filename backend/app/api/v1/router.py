"""
OpsPulse Backend — API v1 Router

Aggregates all v1 endpoint routers into a single router.
Registered in main.py with the /api/v1 prefix.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import agents, alerts, audit, auth, health, incidents, metrics, users

api_router = APIRouter()

# Health endpoints — always first, no auth required
api_router.include_router(health.router, tags=["health"])

# Authentication & Session Management
api_router.include_router(auth.router, tags=["auth"])

# User Management (Admin Only)
api_router.include_router(users.router, tags=["users"])

# Agent Management & Registration
api_router.include_router(agents.router, tags=["agents"])

# Metric Ingestion & Query
api_router.include_router(metrics.router, tags=["metrics"])

# Alert Rules (Admin/Operator)
api_router.include_router(alerts.router, tags=["alerts"])

# Incidents (All Roles Read, Admin/Operator Transitions)
api_router.include_router(incidents.router, tags=["incidents"])

# Audit Trail (Admin Only)
api_router.include_router(audit.router, tags=["audit"])
