"""
OpsPulse Agent — Tests: Configuration Module
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from opspulse_agent.config import AgentConfig


def test_agent_config_defaults() -> None:
    """Verifies sensible starter defaults."""
    config = AgentConfig()
    assert config.agent.name == "ubuntu-primary"
    assert config.agent.collection_interval_seconds == 10
    assert config.agent.batch_size == 10
    assert config.agent.local_buffer_max_batches == 100
    assert config.backend.base_url == "http://localhost:8000"
    assert config.backend.heartbeat_interval_seconds == 30
    assert config.features.cpu is True
    assert config.features.memory is True
    assert config.features.disk is True
    assert config.features.network is True


def test_agent_config_from_yaml_file(tmp_path: Path) -> None:
    """Verifies reading custom YAML config."""
    yaml_content = """
agent:
  name: custom-server
  collection_interval_seconds: 5
  batch_size: 2
backend:
  base_url: http://monitoring.internal:8000
"""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_content, encoding="utf-8")

    config = AgentConfig.load_from_file(cfg_file)
    assert config.agent.name == "custom-server"
    assert config.agent.collection_interval_seconds == 5
    assert config.agent.batch_size == 2
    assert config.backend.base_url == "http://monitoring.internal:8000"


def test_agent_config_env_variable_overrides() -> None:
    """Verifies that environment variables override configuration."""
    with patch.dict(
        os.environ,
        {
            "AGENT_NAME": "env-override-host",
            "AGENT_ID": "agent-uuid-1234",
            "AGENT_SECRET": "secret-token-xyz",
            "BACKEND_BASE_URL": "http://api.remote:8000",
            "LOG_LEVEL": "DEBUG",
        },
    ):
        config = AgentConfig.load_from_file()
        assert config.agent.name == "env-override-host"
        assert config.backend.agent_id == "agent-uuid-1234"
        assert config.backend.agent_secret == "secret-token-xyz"
        assert config.backend.base_url == "http://api.remote:8000"
        assert config.logging.level == "DEBUG"
