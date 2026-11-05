"""
OpsPulse Host Monitoring Agent — Ingestion Metric Contract

Defines the Pydantic schemas for metric samples and batches sent to
POST /api/v1/metrics/ingest. Matches spec Section 10.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from opspulse_agent.collectors.cpu import CpuMetrics
from opspulse_agent.collectors.disk import DiskItem
from opspulse_agent.collectors.memory import MemoryMetrics
from opspulse_agent.collectors.network import NetworkInterfaceItem


class MetricSample(BaseModel):
    """A single time-stamped telemetry observation."""

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC sample acquisition timestamp",
    )
    cpu: CpuMetrics | None = None
    memory: MemoryMetrics | None = None
    disks: list[DiskItem] = Field(default_factory=list)
    networks: list[NetworkInterfaceItem] = Field(default_factory=list)


class MetricBatch(BaseModel):
    """Batch of metric samples transmitted to the central backend."""

    agent_id: str = Field(..., description="Unique agent identifier (UUID string)")
    batch_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Idempotency key for this batch (UUID string)",
    )
    metrics: list[MetricSample] = Field(
        ..., min_length=1, description="List of collected telemetry samples"
    )

