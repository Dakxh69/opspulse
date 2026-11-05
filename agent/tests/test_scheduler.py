"""
OpsPulse Agent — Tests: Agent Scheduler & Buffer
"""

from __future__ import annotations

from unittest.mock import MagicMock

from opspulse_agent.config import AgentConfig
from opspulse_agent.scheduler import AgentScheduler


def test_scheduler_batching_and_buffering() -> None:
    """Verifies that samples accumulate and convert to batches when batch_size is reached."""
    config = AgentConfig()
    config.agent.batch_size = 2
    config.agent.local_buffer_max_batches = 5
    config.backend.agent_id = "agent-unit-test"

    mock_api = MagicMock()
    mock_api.send_metrics.return_value = True
    mock_api.send_heartbeat.return_value = True

    scheduler = AgentScheduler(config, api_client=mock_api)

    # First sample: not batched yet
    scheduler.tick_collection()
    assert len(scheduler.current_samples) == 1
    assert len(scheduler.buffer) == 0

    # Second sample: reaches batch_size 2 -> enqueued into buffer
    scheduler.tick_collection()
    assert len(scheduler.current_samples) == 0
    assert len(scheduler.buffer) == 1
    assert scheduler.buffer[0].agent_id == "agent-unit-test"
    assert len(scheduler.buffer[0].metrics) == 2


def test_scheduler_flush_buffer_offline_retention() -> None:
    """Verifies that if API fails, batches remain retained in local buffer."""
    config = AgentConfig()
    config.agent.batch_size = 1
    config.agent.local_buffer_max_batches = 3

    mock_api = MagicMock()
    mock_api.send_metrics.return_value = False  # Backend down!

    scheduler = AgentScheduler(config, api_client=mock_api)

    # Generate 3 batches
    scheduler.tick_collection()
    scheduler.tick_collection()
    scheduler.tick_collection()

    assert len(scheduler.buffer) == 3

    # Flush fails; all 3 remain safely in buffer
    sent = scheduler.flush_buffer()
    assert sent == 0
    assert len(scheduler.buffer) == 3

    # Backend recovers
    mock_api.send_metrics.return_value = True
    sent = scheduler.flush_buffer()
    assert sent == 3
    assert len(scheduler.buffer) == 0


def test_scheduler_buffer_max_depth_drops_oldest() -> None:
    """Verifies bounded deque drops oldest batch when max_batches is exceeded."""
    config = AgentConfig()
    config.agent.batch_size = 1
    config.agent.local_buffer_max_batches = 2

    mock_api = MagicMock()
    scheduler = AgentScheduler(config, api_client=mock_api)

    scheduler.tick_collection()
    first_batch_id = scheduler.buffer[0].batch_id

    scheduler.tick_collection()
    scheduler.tick_collection()  # Exceeds max 2; oldest dropped

    assert len(scheduler.buffer) == 2
    buffered_ids = [b.batch_id for b in scheduler.buffer]
    assert first_batch_id not in buffered_ids
