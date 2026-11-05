"""
OpsPulse Backend — Metric Ingestion Schemas

Defines Pydantic schemas validating telemetry samples and batches submitted
by monitored agents. Strictly mirrors agent payload specification (Section 8 & 10).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


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
    """CPU telemetry schema."""

    usage_percent: float = Field(..., ge=0.0, le=100.0)
    per_core_percent: list[float] = Field(default_factory=list)
    logical_cores: int = Field(..., gt=0)
    physical_cores: int | None = None
    frequency: CpuFrequency | None = None
    load_average: CpuLoadAverage | None = None


class SwapMetrics(BaseModel):
    """Swap memory schema."""

    total_bytes: int = Field(..., ge=0)
    used_bytes: int = Field(..., ge=0)
    free_bytes: int = Field(..., ge=0)
    usage_percent: float = Field(..., ge=0.0, le=100.0)


class MemoryMetrics(BaseModel):
    """RAM and swap telemetry schema."""

    total_bytes: int = Field(..., gt=0)
    used_bytes: int = Field(..., ge=0)
    available_bytes: int = Field(..., ge=0)
    usage_percent: float = Field(..., ge=0.0, le=100.0)
    free_bytes: int = Field(..., ge=0)
    cached_bytes: int | None = None
    buffers_bytes: int | None = None
    swap: SwapMetrics | None = None


class DiskItem(BaseModel):
    """Mounted filesystem telemetry schema."""

    mount_point: str
    device: str
    fstype: str
    total_bytes: int = Field(..., gt=0)
    used_bytes: int = Field(..., ge=0)
    free_bytes: int = Field(..., ge=0)
    usage_percent: float = Field(..., ge=0.0, le=100.0)


class NetworkInterfaceItem(BaseModel):
    """Network interface counters and computed rate telemetry schema."""

    name: str
    bytes_sent: int = Field(..., ge=0)
    bytes_recv: int = Field(..., ge=0)
    packets_sent: int = Field(..., ge=0)
    packets_recv: int = Field(..., ge=0)
    errin: int = Field(..., ge=0)
    errout: int = Field(..., ge=0)
    dropin: int = Field(..., ge=0)
    dropout: int = Field(..., ge=0)
    bytes_sent_per_sec: float = Field(default=0.0, ge=0.0)
    bytes_recv_per_sec: float = Field(default=0.0, ge=0.0)
    packets_sent_per_sec: float = Field(default=0.0, ge=0.0)
    packets_recv_per_sec: float = Field(default=0.0, ge=0.0)


class MetricSample(BaseModel):
    """Single observation timestamped in UTC."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    cpu: CpuMetrics | None = None
    memory: MemoryMetrics | None = None
    disks: list[DiskItem] = Field(default_factory=list)
    networks: list[NetworkInterfaceItem] = Field(default_factory=list)


class MetricBatch(BaseModel):
    """Batch of metric samples submitted by an agent."""

    agent_id: str
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metrics: list[MetricSample] = Field(..., min_length=1, max_length=100)


class IngestionResponse(BaseModel):
    """Acknowledgment returned upon successful receipt and queueing of metric batch."""

    model_config = ConfigDict(from_attributes=True)

    status: str = "accepted"
    batch_id: str
    samples_received: int


class MetricDiskResponse(BaseModel):
    """Disk partition metric response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mount_point: str
    device: str
    fstype: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float


class MetricNetworkResponse(BaseModel):
    """Network interface metric response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interface_name: str
    bytes_sent: int
    bytes_recv: int
    bytes_sent_per_sec: float
    bytes_recv_per_sec: float
    packets_sent_per_sec: float
    packets_recv_per_sec: float


class MetricRecordResponse(BaseModel):
    """Point-in-time telemetry snapshot response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_percent: float
    disks: list[MetricDiskResponse] = Field(default_factory=list)
    networks: list[MetricNetworkResponse] = Field(default_factory=list)


class MetricSummaryResponse(BaseModel):
    """Statistical summary over a designated time range."""

    agent_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    sample_count: int
    avg_cpu_percent: float | None = None
    max_cpu_percent: float | None = None
    min_cpu_percent: float | None = None
    avg_memory_percent: float | None = None
    max_memory_percent: float | None = None
    min_memory_percent: float | None = None
