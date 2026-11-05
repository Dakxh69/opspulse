"""
OpsPulse Host Monitoring Agent — Tests: Network Collector

Verifies:
- Live network interface counter collection on host.
- Throughput rate calculation (bytes/sec, packets/sec) from consecutive samples.
- Counter reset handling (reboot or counter wrap-around).
- Optional loopback filtering.
- Pydantic bounds validation.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from opspulse_agent.collectors.network import (
    NetworkCollector,
    NetworkInterfaceItem,
)


def test_network_collector_live_collection() -> None:
    """Verifies live network counters collection on host."""
    collector = NetworkCollector(include_loopback=True)
    time.sleep(0.1)
    items = collector.collect()

    assert isinstance(items, list)
    assert len(items) >= 1  # At least loopback or physical eth exists
    for item in items:
        assert isinstance(item, NetworkInterfaceItem)
        assert item.bytes_sent >= 0
        assert item.bytes_recv >= 0
        assert item.bytes_sent_per_sec >= 0.0


def test_network_collector_rate_calculation() -> None:
    """Verifies that counter deltas divided by elapsed seconds compute exact rates."""
    snap1 = MagicMock()
    snap1.bytes_sent = 1_000_000
    snap1.bytes_recv = 2_000_000
    snap1.packets_sent = 1_000
    snap1.packets_recv = 2_000
    snap1.errin = 0
    snap1.errout = 0
    snap1.dropin = 0
    snap1.dropout = 0

    snap2 = MagicMock()
    snap2.bytes_sent = 1_050_000  # +50,000 bytes over 2.0s = 25,000 bytes/sec
    snap2.bytes_recv = 2_100_000  # +100,000 bytes over 2.0s = 50,000 bytes/sec
    snap2.packets_sent = 1_050  # +50 packets over 2.0s = 25 packets/sec
    snap2.packets_recv = 2_100  # +100 packets over 2.0s = 50 packets/sec
    snap2.errin = 0
    snap2.errout = 0
    snap2.dropin = 0
    snap2.dropout = 0

    with (
        patch("psutil.net_io_counters", side_effect=[{"eth0": snap1}, {"eth0": snap2}]),
        patch("time.monotonic", side_effect=[100.0, 102.0]),  # 2.0 seconds elapsed
    ):
        collector = NetworkCollector()
        items = collector.collect()

        assert len(items) == 1
        item = items[0]
        assert item.name == "eth0"
        assert item.bytes_sent_per_sec == 25_000.0
        assert item.bytes_recv_per_sec == 50_000.0
        assert item.packets_sent_per_sec == 25.0
        assert item.packets_recv_per_sec == 50.0


def test_network_collector_counter_reset() -> None:
    """Verifies that counter resets (current < previous) reset rates to 0.0."""
    snap_before = MagicMock()
    snap_before.bytes_sent = 10_000_000
    snap_before.bytes_recv = 10_000_000
    snap_before.packets_sent = 5_000
    snap_before.packets_recv = 5_000
    snap_before.errin = 0
    snap_before.errout = 0
    snap_before.dropin = 0
    snap_before.dropout = 0

    # System rebooted or interface restarted: counters dropped back near 0
    snap_reset = MagicMock()
    snap_reset.bytes_sent = 1_000
    snap_reset.bytes_recv = 2_000
    snap_reset.packets_sent = 10
    snap_reset.packets_recv = 20
    snap_reset.errin = 0
    snap_reset.errout = 0
    snap_reset.dropin = 0
    snap_reset.dropout = 0

    with (
        patch("psutil.net_io_counters", side_effect=[{"eth0": snap_before}, {"eth0": snap_reset}]),
        patch("time.monotonic", side_effect=[50.0, 55.0]),
    ):
        collector = NetworkCollector()
        items = collector.collect()

        assert len(items) == 1
        item = items[0]
        # Rates should stay 0.0 rather than going negative
        assert item.bytes_sent_per_sec == 0.0
        assert item.bytes_recv_per_sec == 0.0


def test_network_collector_loopback_filter() -> None:
    """Verifies that 'lo' is excluded by default, but included if specified."""
    mock_stats = MagicMock()
    mock_stats.bytes_sent = 100
    mock_stats.bytes_recv = 100
    mock_stats.packets_sent = 1
    mock_stats.packets_recv = 1
    mock_stats.errin = 0
    mock_stats.errout = 0
    mock_stats.dropin = 0
    mock_stats.dropout = 0

    with patch("psutil.net_io_counters", return_value={"lo": mock_stats, "eth0": mock_stats}):
        # Default: lo excluded
        c1 = NetworkCollector(include_loopback=False)
        items1 = c1.collect()
        names1 = [it.name for it in items1]
        assert "lo" not in names1
        assert "eth0" in names1

        # Enabled: lo included
        c2 = NetworkCollector(include_loopback=True)
        items2 = c2.collect()
        names2 = [it.name for it in items2]
        assert "lo" in names2
        assert "eth0" in names2


def test_network_item_validation() -> None:
    """Verifies Pydantic boundaries on network metrics."""
    with pytest.raises(ValidationError):
        NetworkInterfaceItem(
            name="eth0",
            bytes_sent=-1,  # Negative bytes rejected
            bytes_recv=100,
            packets_sent=1,
            packets_recv=1,
            errin=0,
            errout=0,
            dropin=0,
            dropout=0,
        )
