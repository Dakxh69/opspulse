"""
OpsPulse Host Monitoring Agent — Memory Metric Collector

Collects RAM and Swap telemetry per spec Section 8.2:
- Total RAM (bytes)
- Used RAM (bytes)
- Available RAM (bytes)
- Memory utilization percentage
- Swap total (bytes)
- Swap used (bytes)
- Swap utilization percentage

Design Decisions:
- Handles systems without swap enabled (swap.total == 0) gracefully.
- Collects Linux-specific cached and buffers memory for deep diagnostics.
- Uses Pydantic for validation of byte values (>= 0) and percentages (0.0 to 100.0).
"""

from __future__ import annotations

import psutil
from pydantic import BaseModel, Field


class SwapMetrics(BaseModel):
    """Swap memory measurements in bytes and percentage."""

    total_bytes: int = Field(..., ge=0, description="Total swap memory in bytes")
    used_bytes: int = Field(..., ge=0, description="Used swap memory in bytes")
    free_bytes: int = Field(..., ge=0, description="Free swap memory in bytes")
    usage_percent: float = Field(..., ge=0.0, le=100.0, description="Swap utilization percentage")


class MemoryMetrics(BaseModel):
    """Structured RAM and Swap metric payload ready for serialization."""

    total_bytes: int = Field(..., gt=0, description="Total physical RAM in bytes")
    used_bytes: int = Field(..., ge=0, description="Used RAM in bytes")
    available_bytes: int = Field(
        ..., ge=0, description="Available RAM in bytes (usable without swapping)"
    )
    usage_percent: float = Field(..., ge=0.0, le=100.0, description="RAM utilization percentage")
    free_bytes: int = Field(..., ge=0, description="Unallocated free RAM in bytes")
    cached_bytes: int | None = Field(
        None, ge=0, description="Memory used for filesystem cache (Linux)"
    )
    buffers_bytes: int | None = Field(
        None, ge=0, description="Memory used for block buffers (Linux)"
    )
    swap: SwapMetrics | None = Field(None, description="Swap space metrics (if configured on host)")


class MemoryCollector:
    """Collects physical RAM and swap memory metrics using psutil."""

    def collect(self) -> MemoryMetrics:
        """Collect current RAM and swap metrics."""
        vm = psutil.virtual_memory()

        # Swap memory (may be empty or 0 bytes if swap is disabled)
        swap_info: SwapMetrics | None = None
        try:
            sm = psutil.swap_memory()
            if sm.total > 0:
                swap_usage = float(sm.percent)
            else:
                swap_usage = 0.0

            swap_info = SwapMetrics(
                total_bytes=int(sm.total),
                used_bytes=int(sm.used),
                free_bytes=int(sm.free),
                usage_percent=swap_usage,
            )
        except Exception:
            swap_info = None

        return MemoryMetrics(
            total_bytes=int(vm.total),
            used_bytes=int(vm.used),
            available_bytes=int(vm.available),
            usage_percent=float(vm.percent),
            free_bytes=int(vm.free),
            cached_bytes=getattr(vm, "cached", None),
            buffers_bytes=getattr(vm, "buffers", None),
            swap=swap_info,
        )
