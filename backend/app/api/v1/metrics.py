"""
OpsPulse Backend — Metric Ingestion & Query Endpoints

Provides:
- POST /metrics/ingest: Authenticated telemetry ingestion pipeline receiving
  batches of metric samples from monitored host agents.
- GET  /metrics/{agent_id}: Query historical telemetry records with time filters.
- GET  /metrics/{agent_id}/latest: Retrieve the most recent telemetry sample.
- GET  /metrics/{agent_id}/summary: Aggregate summary statistics over a time window.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_agent, get_current_user
from app.database.session import get_db
from app.models.agent import Agent
from app.models.metric import MetricRecord
from app.models.user import User
from app.schemas.metrics import (
    IngestionResponse,
    MetricBatch,
    MetricRecordResponse,
    MetricSummaryResponse,
)
from app.workers.tasks import process_metric_batch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post(
    "/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest batch of host telemetry metrics",
)
async def ingest_metrics(
    batch: MetricBatch,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Receives, validates, and queues authenticated metric batches in Celery/Redis.
    Ensures agent identity in payload matches caller's authenticated identity.
    Returns 503 Service Unavailable if the queue broker cannot be reached.
    """
    if batch.agent_id != str(current_agent.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload agent_id does not match authenticated agent credentials",
        )

    try:
        metrics_data = [m.model_dump(mode="json") for m in batch.metrics]
        process_metric_batch.delay(
            agent_id=str(current_agent.id),
            batch_id=batch.batch_id,
            metrics_payload=metrics_data,
        )
    except Exception as exc:
        logger.error("Failed to enqueue metric batch in Celery/Redis", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metric queue is temporarily unavailable. Retry with buffered data.",
        ) from exc

    return IngestionResponse(
        status="accepted",
        batch_id=batch.batch_id,
        samples_received=len(batch.metrics),
    )


@router.get(
    "/{agent_id}",
    response_model=list[MetricRecordResponse],
    summary="Query historical telemetry records for an agent",
)
async def get_metrics_history(
    agent_id: uuid.UUID,
    start_time: datetime | None = Query(None, description="Earliest UTC timestamp"),
    end_time: datetime | None = Query(None, description="Latest UTC timestamp"),
    limit: int = Query(100, ge=1, le=1000, description="Max samples to return"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MetricRecordResponse]:
    """Retrieves paginated historical metric snapshots bounded by time."""
    stmt = select(MetricRecord).where(MetricRecord.agent_id == agent_id)

    if start_time:
        stmt = stmt.where(MetricRecord.timestamp >= start_time)
    if end_time:
        stmt = stmt.where(MetricRecord.timestamp <= end_time)

    stmt = stmt.order_by(MetricRecord.timestamp.desc()).limit(limit)
    result = await db.execute(stmt)
    records = result.scalars().all()

    return [MetricRecordResponse.model_validate(r) for r in records]


@router.get(
    "/{agent_id}/latest",
    response_model=MetricRecordResponse,
    summary="Retrieve the most recent metric sample for an agent",
)
async def get_latest_metrics(
    agent_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MetricRecordResponse:
    """Returns the single latest telemetry record for the requested agent."""
    stmt = (
        select(MetricRecord)
        .where(MetricRecord.agent_id == agent_id)
        .order_by(MetricRecord.timestamp.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No metrics found for this agent",
        )

    return MetricRecordResponse.model_validate(record)


@router.get(
    "/{agent_id}/summary",
    response_model=MetricSummaryResponse,
    summary="Retrieve statistical averages/summary for an agent",
)
async def get_metrics_summary(
    agent_id: uuid.UUID,
    hours: int = Query(24, ge=1, le=720, description="Evaluation window in hours"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MetricSummaryResponse:
    """Computes summary statistics (min, max, avg) for CPU and memory."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=hours)

    stmt = select(
        func.count(MetricRecord.id),
        func.avg(MetricRecord.cpu_usage_percent),
        func.max(MetricRecord.cpu_usage_percent),
        func.min(MetricRecord.cpu_usage_percent),
        func.avg(MetricRecord.memory_usage_percent),
        func.max(MetricRecord.memory_usage_percent),
        func.min(MetricRecord.memory_usage_percent),
    ).where(
        MetricRecord.agent_id == agent_id,
        MetricRecord.timestamp >= start_time,
        MetricRecord.timestamp <= end_time,
    )
    result = await db.execute(stmt)
    row = result.one()

    count = row[0] or 0
    return MetricSummaryResponse(
        agent_id=agent_id,
        start_time=start_time,
        end_time=end_time,
        sample_count=count,
        avg_cpu_percent=round(float(row[1]), 2) if row[1] is not None else None,
        max_cpu_percent=round(float(row[2]), 2) if row[2] is not None else None,
        min_cpu_percent=round(float(row[3]), 2) if row[3] is not None else None,
        avg_memory_percent=round(float(row[4]), 2) if row[4] is not None else None,
        max_memory_percent=round(float(row[5]), 2) if row[5] is not None else None,
        min_memory_percent=round(float(row[6]), 2) if row[6] is not None else None,
    )
