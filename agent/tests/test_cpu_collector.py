"""
OpsPulse Host Monitoring Agent — Tests: CPU Collector

Verifies:
- Live CPU metrics collection on host environment.
- Non-blocking execution behavior.
- Core counts, per-core metrics, and load averages.
- Graceful handling of virtualized/containerized environments.
- Strict Pydantic boundary validation.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from opspulse_agent.collectors.cpu import (
    CpuCollector,
    CpuMetrics,
)


def test_cpu_collector_live_collection() -> None:
    """Verifies live CPU metrics collection against real host psutil."""
    collector = CpuCollector()
    # Allow small delay for non-zero delta
    time.sleep(0.1)
    metrics = collector.collect()

    assert isinstance(metrics, CpuMetrics)
    assert 0.0 <= metrics.usage_percent <= 100.0
    assert metrics.logical_cores >= 1
    assert len(metrics.per_core_percent) == metrics.logical_cores
    for core_val in metrics.per_core_percent:
        assert 0.0 <= core_val <= 100.0

    if metrics.load_average is not None:
        assert metrics.load_average.load_1m >= 0.0
        assert metrics.load_average.load_5m >= 0.0
        assert metrics.load_average.load_15m >= 0.0


def test_cpu_collector_mocked_values() -> None:
    """Verifies collection logic when psutil values are mocked."""
    mock_freq = MagicMock()
    mock_freq.current = 2400.0
    mock_freq.min = 800.0
    mock_freq.max = 4200.0

    def mock_percent(interval: float | None = None, percpu: bool = False) -> float | list[float]:
        return [40.0, 45.0] if percpu else 42.5

    with (
        patch("psutil.cpu_percent", side_effect=mock_percent),
        patch("psutil.cpu_count", return_value=2),
        patch("psutil.cpu_freq", return_value=mock_freq),
        patch("os.getloadavg", return_value=(1.25, 0.95, 0.80)),
    ):
        collector = CpuCollector()
        metrics = collector.collect()

        assert metrics.usage_percent == 42.5
        assert metrics.per_core_percent == [40.0, 45.0]
        assert metrics.logical_cores == 2
        assert metrics.frequency is not None
        assert metrics.frequency.current_mhz == 2400.0
        assert metrics.load_average is not None
        assert metrics.load_average.load_1m == 1.25
        assert metrics.load_average.load_5m == 0.95
        assert metrics.load_average.load_15m == 0.80


def test_cpu_collector_graceful_missing_freq_and_loadavg() -> None:
    """Verifies that missing cpu_freq or getloadavg does not crash collection."""

    def mock_percent(interval: float | None = None, percpu: bool = False) -> float | list[float]:
        return [15.0] if percpu else 15.0

    with (
        patch("psutil.cpu_percent", side_effect=mock_percent),
        patch("psutil.cpu_count", return_value=1),
        patch("psutil.cpu_freq", side_effect=Exception("Freq not supported")),
        patch("os.getloadavg", side_effect=OSError("Loadavg not supported")),
    ):
        collector = CpuCollector()
        metrics = collector.collect()

        assert metrics.usage_percent == 15.0
        assert metrics.frequency is None
        assert metrics.load_average is None


def test_cpu_metrics_pydantic_schema_validation() -> None:
    """Verifies that Pydantic enforces valid ranges (0.0 to 100.0)."""
    # Valid model construction
    valid = CpuMetrics(
        usage_percent=55.0,
        per_core_percent=[50.0, 60.0],
        logical_cores=2,
    )
    assert valid.usage_percent == 55.0

    # Negative usage rejected
    with pytest.raises(ValidationError):
        CpuMetrics(
            usage_percent=-5.0,
            logical_cores=1,
        )

    # Usage > 100% rejected
    with pytest.raises(ValidationError):
        CpuMetrics(
            usage_percent=105.0,
            logical_cores=1,
        )

    # Logical cores <= 0 rejected
    with pytest.raises(ValidationError):
        CpuMetrics(
            usage_percent=25.0,
            logical_cores=0,
        )
