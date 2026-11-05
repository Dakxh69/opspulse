"""
OpsPulse Agent — Collectors Package
"""

from opspulse_agent.collectors.cpu import (
    CpuCollector,
    CpuFrequency,
    CpuLoadAverage,
    CpuMetrics,
)

__all__ = [
    "CpuCollector",
    "CpuFrequency",
    "CpuLoadAverage",
    "CpuMetrics",
]
