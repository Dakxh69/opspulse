"""
OpsPulse Host Monitoring Agent — Configuration Module

Loads and validates agent configuration from YAML files and environment variables.
Credentials (AGENT_SECRET) are loaded from environment variables or a separate secure file,
never checked into version control. See spec Section 8.6.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AgentSettings(BaseModel):
    """General agent identity and scheduling intervals."""

    name: str = Field(default="ubuntu-primary", description="Host display name")
    collection_interval_seconds: int = Field(
        default=10, ge=1, le=3600, description="Metric collection frequency in seconds"
    )
    batch_size: int = Field(
        default=10, ge=1, le=1000, description="Number of samples to batch before sending"
    )
    local_buffer_max_batches: int = Field(
        default=100, ge=1, le=10000, description="Max batches to buffer during outages"
    )


class BackendSettings(BaseModel):
    """Backend connection and authentication settings."""

    base_url: str = Field(default="http://localhost:8000", description="Base URL of OpsPulse API")
    heartbeat_interval_seconds: int = Field(
        default=30, ge=5, le=3600, description="Heartbeat ping interval in seconds"
    )
    agent_id: str | None = Field(default=None, description="Provisioned Agent UUID")
    agent_secret: str | None = Field(
        default=None, description="Secret token returned on provisioning"
    )
    timeout_seconds: float = Field(
        default=10.0, ge=1.0, le=120.0, description="HTTP request timeout"
    )


class FeatureSettings(BaseModel):
    """Toggle metric subsystems."""

    cpu: bool = True
    memory: bool = True
    disk: bool = True
    network: bool = True
    processes: bool = False


class LoggingSettings(BaseModel):
    """Agent logging configuration."""

    level: str = "INFO"


class AgentConfig(BaseModel):
    """Complete root configuration for OpsPulse agent."""

    agent: AgentSettings = Field(default_factory=AgentSettings)
    backend: BackendSettings = Field(default_factory=BackendSettings)
    features: FeatureSettings = Field(default_factory=FeatureSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @classmethod
    def load_from_file(cls, path: str | Path | None = None) -> AgentConfig:
        """Load configuration from a YAML file, overlaid with environment variables."""
        data: dict[str, Any] = {}

        if path is not None and Path(path).is_file():
            with open(path, encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    data = loaded

        config = cls.model_validate(data)

        # Overlay environment variables if present
        if "AGENT_NAME" in os.environ:
            config.agent.name = os.environ["AGENT_NAME"]
        if "AGENT_ID" in os.environ:
            config.backend.agent_id = os.environ["AGENT_ID"]
        if "AGENT_SECRET" in os.environ:
            config.backend.agent_secret = os.environ["AGENT_SECRET"]
        if "BACKEND_BASE_URL" in os.environ:
            config.backend.base_url = os.environ["BACKEND_BASE_URL"]
        if "LOG_LEVEL" in os.environ:
            config.logging.level = os.environ["LOG_LEVEL"]

        return config
