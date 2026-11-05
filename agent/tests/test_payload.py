"""
OpsPulse Agent — Tests: Ingestion Payload Schemas
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from opspulse_agent.collectors.cpu import CpuMetrics
from opspulse_agent.payload import MetricBatch, MetricSample


def test_metric_sample_defaults() -> None:
    """Verifies MetricSample generates UTC timestamp and default lists."""
    sample = MetricSample()
    assert sample.timestamp is not None
    assert sample.disks == []
    assert sample.networks == []


def test_metric_batch_validation() -> None:
    """Verifies MetricBatch requires agent_id and non-empty samples."""
    sample = MetricSample(
        cpu=CpuMetrics(usage_percent=25.0, per_core_percent=[25.0], logical_cores=1)
    )

    batch = MetricBatch(agent_id="agent-uuid-001", metrics=[sample])
    assert batch.agent_id == "agent-uuid-001"
    assert len(batch.metrics) == 1
    assert batch.batch_id is not None

    # Empty metrics list rejected
    with pytest.raises(ValidationError):
        MetricBatch(agent_id="agent-uuid-001", metrics=[])
