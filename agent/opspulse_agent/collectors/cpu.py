"""
OpsPulse Host Monitoring Agent — CPU Metric Collector

Collects CPU telemetry per spec Section 8.1:
- Overall CPU utilization percentage.
- Per-core utilization percentages.
- Logical and physical core counts.
- CPU frequency (current, min, max) where supported by OS.
- System load averages (1m, 5m, 15m) where supported.

Design Decisions:
- Uses non-blocking sampling (`interval=None`): the first call initializes counters
  and returns 0.0 or a baseline, while subsequent calls return the delta since the
  last call without blocking the agent event loop.
- Gracefully handles virtualized environments where cpu_freq or physical_cores
  may return None.
"""

from __future__ import annotations

import os

import psutil
from pydantic import BaseModel, Field


class CpuFrequency(BaseModel):
    """CPU frequency measurements in MHz."""

    current_mhz: float | None = None
    min_mhz: float | None = None
    max_mhz: float | None = None


class CpuLoadAverage(BaseModel):
    """System load averages over 1, 5, and 15-minute intervals."""

    load_1m: float
    load_5m: float
    load_15m: float


class CpuMetrics(BaseModel):
    """Structured CPU metric payload ready for serialization."""

    usage_percent: float = Field(
        ..., ge=0.0, le=100.0, description="Overall CPU utilization percentage"
    )
    per_core_percent: list[float] = Field(
        default_factory=list, description="Per-core utilization percentages"
    )
    logical_cores: int = Field(..., gt=0, description="Number of logical CPU cores")
    physical_cores: int | None = Field(
        None, description="Number of physical CPU cores (if identifiable)"
    )
    frequency: CpuFrequency | None = Field(None, description="Current CPU frequency in MHz")
    load_average: CpuLoadAverage | None = Field(
        None, description="System load average (1m, 5m, 15m)"
    )


class CpuCollector:
    """Collects CPU metrics using psutil without blocking the runtime loop."""

    def __init__(self) -> None:
        # Prime psutil internal counters so the first sample has a starting baseline
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)
        self._logical_cores = psutil.cpu_count(logical=True) or 1
        self._physical_cores = psutil.cpu_count(logical=False)

    def collect(self) -> CpuMetrics:
        """Collect current CPU metrics. Non-blocking."""
        # Overall CPU usage percentage
        overall_usage = float(psutil.cpu_percent(interval=None))

        # Per-core utilization percentages
        per_core_raw = psutil.cpu_percent(interval=None, percpu=True)
        per_core = [float(val) for val in per_core_raw]

        # CPU frequency (may return None on certain VMs/containers)
        freq_info: CpuFrequency | None = None
        try:
            freq_raw = psutil.cpu_freq()
            if freq_raw is not None:
                freq_info = CpuFrequency(
                    current_mhz=round(float(freq_raw.current), 2) if freq_raw.current else None,
                    min_mhz=round(float(freq_raw.min), 2) if freq_raw.min else None,
                    max_mhz=round(float(freq_raw.max), 2) if freq_raw.max else None,
                )
        except Exception:
            freq_info = None

        # System load average (Linux/Unix)
        load_avg: CpuLoadAverage | None = None
        try:
            if hasattr(os, "getloadavg"):
                l1, l5, l15 = os.getloadavg()
                load_avg = CpuLoadAverage(
                    load_1m=round(float(l1), 2),
                    load_5m=round(float(l5), 2),
                    load_15m=round(float(l15), 2),
                )
        except Exception:
            load_avg = None

        return CpuMetrics(
            usage_percent=overall_usage,
            per_core_percent=per_core,
            logical_cores=self._logical_cores,
            physical_cores=self._physical_cores,
            frequency=freq_info,
            load_average=load_avg,
        )
