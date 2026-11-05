"""
OpsPulse Host Monitoring Agent — Tests: Memory Collector

Verifies:
- Live RAM and Swap metrics collection against real host psutil.
- Handling of systems with zero swap enabled (e.g., containers, bare VMs).
- Error resilience if swap information is unavailable.
- Strict Pydantic validation on byte counts and percentage bounds.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from opspulse_agent.collectors.memory import (
    MemoryCollector,
    MemoryMetrics,
    SwapMetrics,
)


def test_memory_collector_live_collection() -> None:
    """Verifies live RAM and Swap metrics collection on host machine."""
    collector = MemoryCollector()
    metrics = collector.collect()

    assert isinstance(metrics, MemoryMetrics)
    assert metrics.total_bytes > 0
    assert metrics.used_bytes >= 0
    assert metrics.available_bytes >= 0
    assert 0.0 <= metrics.usage_percent <= 100.0
    assert metrics.free_bytes >= 0

    if metrics.swap is not None:
        assert isinstance(metrics.swap, SwapMetrics)
        assert metrics.swap.total_bytes >= 0
        assert metrics.swap.used_bytes >= 0
        assert metrics.swap.free_bytes >= 0
        assert 0.0 <= metrics.swap.usage_percent <= 100.0


def test_memory_collector_mocked_values() -> None:
    """Verifies collection logic when psutil memory structures are mocked."""
    mock_vm = MagicMock()
    mock_vm.total = 16_000_000_000
    mock_vm.used = 10_000_000_000
    mock_vm.available = 6_000_000_000
    mock_vm.percent = 62.5
    mock_vm.free = 4_000_000_000
    mock_vm.cached = 1_500_000_000
    mock_vm.buffers = 500_000_000

    mock_swap = MagicMock()
    mock_swap.total = 4_000_000_000
    mock_swap.used = 1_000_000_000
    mock_swap.free = 3_000_000_000
    mock_swap.percent = 25.0

    with (
        patch("psutil.virtual_memory", return_value=mock_vm),
        patch("psutil.swap_memory", return_value=mock_swap),
    ):
        collector = MemoryCollector()
        metrics = collector.collect()

        assert metrics.total_bytes == 16_000_000_000
        assert metrics.used_bytes == 10_000_000_000
        assert metrics.available_bytes == 6_000_000_000
        assert metrics.usage_percent == 62.5
        assert metrics.free_bytes == 4_000_000_000
        assert metrics.cached_bytes == 1_500_000_000
        assert metrics.buffers_bytes == 500_000_000
        assert metrics.swap is not None
        assert metrics.swap.total_bytes == 4_000_000_000
        assert metrics.swap.used_bytes == 1_000_000_000
        assert metrics.swap.free_bytes == 3_000_000_000
        assert metrics.swap.usage_percent == 25.0


def test_memory_collector_zero_swap_support() -> None:
    """Verifies graceful handling of environments where swap is disabled (total == 0)."""
    mock_vm = MagicMock()
    mock_vm.total = 8_000_000_000
    mock_vm.used = 4_000_000_000
    mock_vm.available = 4_000_000_000
    mock_vm.percent = 50.0
    mock_vm.free = 2_000_000_000

    mock_swap = MagicMock()
    mock_swap.total = 0
    mock_swap.used = 0
    mock_swap.free = 0
    mock_swap.percent = 0.0

    with (
        patch("psutil.virtual_memory", return_value=mock_vm),
        patch("psutil.swap_memory", return_value=mock_swap),
    ):
        collector = MemoryCollector()
        metrics = collector.collect()

        assert metrics.swap is not None
        assert metrics.swap.total_bytes == 0
        assert metrics.swap.used_bytes == 0
        assert metrics.swap.free_bytes == 0
        assert metrics.swap.usage_percent == 0.0


def test_memory_collector_swap_exception_fallback() -> None:
    """Verifies that an error in psutil.swap_memory does not fail RAM collection."""
    mock_vm = MagicMock()
    mock_vm.total = 8_000_000_000
    mock_vm.used = 4_000_000_000
    mock_vm.available = 4_000_000_000
    mock_vm.percent = 50.0
    mock_vm.free = 2_000_000_000

    with (
        patch("psutil.virtual_memory", return_value=mock_vm),
        patch("psutil.swap_memory", side_effect=PermissionError("Cannot read swap")),
    ):
        collector = MemoryCollector()
        metrics = collector.collect()

        assert metrics.total_bytes == 8_000_000_000
        assert metrics.usage_percent == 50.0
        assert metrics.swap is None


def test_memory_metrics_validation() -> None:
    """Verifies that Pydantic enforces non-negative byte bounds and percentage limits."""
    # Negative total_bytes rejected
    with pytest.raises(ValidationError):
        MemoryMetrics(
            total_bytes=0,  # total RAM must be > 0
            used_bytes=100,
            available_bytes=100,
            usage_percent=50.0,
            free_bytes=50,
        )

    # Usage percentage > 100.0 rejected
    with pytest.raises(ValidationError):
        MemoryMetrics(
            total_bytes=1000,
            used_bytes=100,
            available_bytes=900,
            usage_percent=100.1,
            free_bytes=900,
        )

    # Negative used_bytes rejected
    with pytest.raises(ValidationError):
        MemoryMetrics(
            total_bytes=1000,
            used_bytes=-50,
            available_bytes=900,
            usage_percent=50.0,
            free_bytes=900,
        )
