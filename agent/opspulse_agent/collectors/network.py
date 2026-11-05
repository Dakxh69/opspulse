"""
OpsPulse Host Monitoring Agent — Network Metric Collector

Collects network telemetry per spec Section 8.4:
- Bytes sent and received counters
- Packets sent and received counters
- Errors (errin, errout) and dropped packets (dropin, dropout)
- Real-time throughput rates (bytes/sec, packets/sec) computed from counter deltas

Design Decisions:
- Handles counter resets (reboots, interface restarts) where current < previous.
- Handles newly appeared or disappeared interfaces without throwing KeyError.
- Loopback interface ('lo') is excluded by default but configurable.
- Uses monotonic clock (time.monotonic) to prevent clock adjustment distortion.
"""

from __future__ import annotations

import time
from typing import NamedTuple

import psutil
from pydantic import BaseModel, Field


class NetworkInterfaceItem(BaseModel):
    """Telemetry counters and computed rates for a single network interface."""

    name: str = Field(..., description="Interface name (e.g. eth0, wlan0, enp3s0)")
    bytes_sent: int = Field(..., ge=0, description="Total cumulative bytes transmitted")
    bytes_recv: int = Field(..., ge=0, description="Total cumulative bytes received")
    packets_sent: int = Field(..., ge=0, description="Total cumulative packets transmitted")
    packets_recv: int = Field(..., ge=0, description="Total cumulative packets received")
    errin: int = Field(..., ge=0, description="Total receive errors")
    errout: int = Field(..., ge=0, description="Total transmit errors")
    dropin: int = Field(..., ge=0, description="Total incoming packets dropped")
    dropout: int = Field(..., ge=0, description="Total outgoing packets dropped")

    # Rates computed from delta / elapsed_time
    bytes_sent_per_sec: float = Field(
        default=0.0, ge=0.0, description="Transmit throughput in bytes/second"
    )
    bytes_recv_per_sec: float = Field(
        default=0.0, ge=0.0, description="Receive throughput in bytes/second"
    )
    packets_sent_per_sec: float = Field(
        default=0.0, ge=0.0, description="Transmit rate in packets/second"
    )
    packets_recv_per_sec: float = Field(
        default=0.0, ge=0.0, description="Receive rate in packets/second"
    )


class _CounterSnapshot(NamedTuple):
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int


class NetworkCollector:
    """Collects per-interface cumulative counters and derives transfer rates."""

    def __init__(self, include_loopback: bool = False) -> None:
        self.include_loopback = include_loopback
        self._prev_counters: dict[str, _CounterSnapshot] = {}
        self._prev_time: float | None = None

        # Prime initial snapshot
        self._prime_initial_state()

    def _prime_initial_state(self) -> None:
        """Records initial counter state so subsequent collection computes deltas."""
        try:
            counters = psutil.net_io_counters(pernic=True)
            self._prev_time = time.monotonic()
            for name, stats in counters.items():
                if not self.include_loopback and name == "lo":
                    continue
                self._prev_counters[name] = _CounterSnapshot(
                    bytes_sent=stats.bytes_sent,
                    bytes_recv=stats.bytes_recv,
                    packets_sent=stats.packets_sent,
                    packets_recv=stats.packets_recv,
                )
        except Exception:
            self._prev_counters = {}
            self._prev_time = None

    def collect(self) -> list[NetworkInterfaceItem]:
        """Collect current counters and calculate rates since previous sample."""
        items: list[NetworkInterfaceItem] = []
        now = time.monotonic()
        elapsed = (now - self._prev_time) if self._prev_time is not None else 0.0

        try:
            counters = psutil.net_io_counters(pernic=True)
        except Exception:
            return items

        new_prev: dict[str, _CounterSnapshot] = {}

        for name, stats in counters.items():
            if not self.include_loopback and name == "lo":
                continue

            current_snapshot = _CounterSnapshot(
                bytes_sent=stats.bytes_sent,
                bytes_recv=stats.bytes_recv,
                packets_sent=stats.packets_sent,
                packets_recv=stats.packets_recv,
            )
            new_prev[name] = current_snapshot

            # Calculate rates if we have previous data for this interface and valid elapsed time
            bytes_sent_rate = 0.0
            bytes_recv_rate = 0.0
            packets_sent_rate = 0.0
            packets_recv_rate = 0.0

            if elapsed > 0.0 and name in self._prev_counters:
                prev = self._prev_counters[name]

                # Check for counter reset (e.g. interface restarted or 32-bit counter rollover)
                if (
                    stats.bytes_sent >= prev.bytes_sent
                    and stats.bytes_recv >= prev.bytes_recv
                    and stats.packets_sent >= prev.packets_sent
                    and stats.packets_recv >= prev.packets_recv
                ):
                    bytes_sent_rate = round((stats.bytes_sent - prev.bytes_sent) / elapsed, 2)
                    bytes_recv_rate = round((stats.bytes_recv - prev.bytes_recv) / elapsed, 2)
                    packets_sent_rate = round((stats.packets_sent - prev.packets_sent) / elapsed, 2)
                    packets_recv_rate = round((stats.packets_recv - prev.packets_recv) / elapsed, 2)
                # Else: counter was reset; rates stay 0.0 for this measurement interval

            items.append(
                NetworkInterfaceItem(
                    name=name,
                    bytes_sent=int(stats.bytes_sent),
                    bytes_recv=int(stats.bytes_recv),
                    packets_sent=int(stats.packets_sent),
                    packets_recv=int(stats.packets_recv),
                    errin=int(stats.errin),
                    errout=int(stats.errout),
                    dropin=int(stats.dropin),
                    dropout=int(stats.dropout),
                    bytes_sent_per_sec=bytes_sent_rate,
                    bytes_recv_per_sec=bytes_recv_rate,
                    packets_sent_per_sec=packets_sent_rate,
                    packets_recv_per_sec=packets_recv_rate,
                )
            )

        self._prev_counters = new_prev
        self._prev_time = now

        return items
