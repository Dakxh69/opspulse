"""
OpsPulse Backend — Asynchronous Celery Tasks

Provides:
- process_metric_batch: Idempotent processing and persistence of ingested telemetry batches.
- cleanup_old_metrics: Scheduled retention enforcement for raw and downsampled metrics.
- downsample_metrics: Periodic downsampling of high-frequency metrics into 5m summary buckets.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from celery import shared_task
from sqlalchemy import delete, func, select

from app.core.config import settings
from app.database.session import SyncSessionLocal
from app.models.metric import MetricAggregate, MetricDisk, MetricNetwork, MetricRecord
from app.models.processed_batch import BatchStatus, ProcessedBatch

logger = logging.getLogger(__name__)


def _parse_utc_datetime(raw: Any) -> datetime:
    """Parses ISO timestamp string or datetime into timezone-aware UTC datetime."""
    if isinstance(raw, datetime):
        return raw if raw.tzinfo is not None else raw.replace(tzinfo=UTC)
    if isinstance(raw, str):
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    return datetime.now(UTC)


@shared_task(  # type: ignore[misc]
    name="app.workers.tasks.process_metric_batch",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_metric_batch(
    self: Any,
    agent_id: str,
    batch_id: str,
    metrics_payload: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Processes an ingested metric batch with strict idempotency and persists records.
    Uses PostgreSQL transaction and sync session.
    """
    agent_uuid = uuid.UUID(agent_id)

    with SyncSessionLocal() as session:
        try:
            # 1. Check idempotency record
            stmt = select(ProcessedBatch).where(
                ProcessedBatch.agent_id == agent_uuid,
                ProcessedBatch.batch_id == batch_id,
            )
            existing = session.execute(stmt).scalar_one_or_none()

            if existing is not None:
                if existing.status == BatchStatus.PROCESSED:
                    logger.info(
                        "Batch already processed; skipping task delivery",
                        extra={"agent_id": agent_id, "batch_id": batch_id},
                    )
                    return {"status": "already_processed", "batch_id": batch_id}

                existing.status = BatchStatus.PROCESSING
                existing.attempt_count += 1
                batch_record = existing
            else:
                batch_record = ProcessedBatch(
                    agent_id=agent_uuid,
                    batch_id=batch_id,
                    status=BatchStatus.PROCESSING,
                    attempt_count=1,
                    received_at=datetime.now(UTC),
                )
                session.add(batch_record)

            session.flush()

            # 2. Persist metric samples transactionally
            records_created = 0
            for sample in metrics_payload:
                sample_time = _parse_utc_datetime(sample.get("timestamp"))

                cpu_data = sample.get("cpu") or {}
                cpu_usage = float(cpu_data.get("usage_percent", 0.0))

                mem_data = sample.get("memory") or {}
                mem_usage = float(mem_data.get("usage_percent", 0.0))

                record = MetricRecord(
                    id=uuid.uuid4(),
                    agent_id=agent_uuid,
                    timestamp=sample_time,
                    cpu_usage_percent=cpu_usage,
                    memory_usage_percent=mem_usage,
                )
                session.add(record)
                session.flush()

                # Persist mounted filesystems
                for disk in sample.get("disks") or []:
                    disk_record = MetricDisk(
                        id=uuid.uuid4(),
                        record_id=record.id,
                        mount_point=disk["mount_point"],
                        device=disk["device"],
                        fstype=disk.get("fstype", "ext4"),
                        total_bytes=int(disk["total_bytes"]),
                        used_bytes=int(disk["used_bytes"]),
                        free_bytes=int(disk["free_bytes"]),
                        usage_percent=float(disk["usage_percent"]),
                    )
                    session.add(disk_record)

                # Persist network interfaces
                for net in sample.get("networks") or []:
                    net_record = MetricNetwork(
                        id=uuid.uuid4(),
                        record_id=record.id,
                        interface_name=net["name"],
                        bytes_sent=int(net["bytes_sent"]),
                        bytes_recv=int(net["bytes_recv"]),
                        bytes_sent_per_sec=float(net.get("bytes_sent_per_sec", 0.0)),
                        bytes_recv_per_sec=float(net.get("bytes_recv_per_sec", 0.0)),
                        packets_sent_per_sec=float(net.get("packets_sent_per_sec", 0.0)),
                        packets_recv_per_sec=float(net.get("packets_recv_per_sec", 0.0)),
                    )
                    session.add(net_record)

                records_created += 1

            # 3. Mark batch as PROCESSED
            batch_record.status = BatchStatus.PROCESSED
            batch_record.processed_at = datetime.now(UTC)
            batch_record.error_summary = None
            session.commit()

            logger.info(
                "Metric batch successfully processed and persisted",
                extra={
                    "agent_id": agent_id,
                    "batch_id": batch_id,
                    "records_created": records_created,
                },
            )
            return {
                "status": "processed",
                "batch_id": batch_id,
                "records_created": records_created,
            }

        except Exception as exc:
            session.rollback()
            logger.error(
                "Error processing metric batch; marking FAILED and retrying",
                extra={"agent_id": agent_id, "batch_id": batch_id, "error": str(exc)},
            )
            try:
                stmt = select(ProcessedBatch).where(
                    ProcessedBatch.agent_id == agent_uuid,
                    ProcessedBatch.batch_id == batch_id,
                )
                fail_record = session.execute(stmt).scalar_one_or_none()
                if fail_record:
                    fail_record.status = BatchStatus.FAILED
                    fail_record.error_summary = str(exc)[:1000]
                    session.commit()
            except Exception:
                session.rollback()

            raise exc


@shared_task(name="app.workers.tasks.cleanup_old_metrics")  # type: ignore[misc]
def cleanup_old_metrics() -> dict[str, int]:
    """
    Enforces retention policies per spec Section 11.1:
    - Raw metric records deleted after METRIC_RAW_RETENTION_DAYS (default 7 days).
    - Aggregated metrics deleted after METRIC_AGGREGATE_RETENTION_DAYS (default 30 days).
    Never deletes incidents, audit logs, or users.
    """
    raw_cutoff = datetime.now(UTC) - timedelta(days=settings.METRIC_RAW_RETENTION_DAYS)
    agg_cutoff = datetime.now(UTC) - timedelta(days=settings.METRIC_AGGREGATE_RETENTION_DAYS)

    with SyncSessionLocal() as session:
        # Delete raw records (cascades to metric_disks and metric_networks)
        del_raw_stmt = delete(MetricRecord).where(MetricRecord.timestamp < raw_cutoff)
        raw_res = session.execute(del_raw_stmt)
        raw_deleted = raw_res.rowcount or 0

        # Delete old aggregates
        del_agg_stmt = delete(MetricAggregate).where(MetricAggregate.bucket_start < agg_cutoff)
        agg_res = session.execute(del_agg_stmt)
        agg_deleted = agg_res.rowcount or 0

        session.commit()

        logger.info(
            "Metric retention cleanup executed",
            extra={"raw_records_deleted": raw_deleted, "aggregates_deleted": agg_deleted},
        )
        return {
            "raw_records_deleted": raw_deleted,
            "aggregates_deleted": agg_deleted,
        }


@shared_task(name="app.workers.tasks.downsample_metrics")  # type: ignore[misc]
def downsample_metrics(window_minutes: int = 60) -> dict[str, int]:
    """
    Aggregates recent raw metric records into 5-minute buckets for metric_aggregates table
    per spec Section 11.1 & Section 17.8.
    """
    now = datetime.now(UTC)
    window_start = now - timedelta(minutes=window_minutes)

    with SyncSessionLocal() as session:
        # Query distinct agents with records in the window
        agents_stmt = (
            select(MetricRecord.agent_id).where(MetricRecord.timestamp >= window_start).distinct()
        )
        agent_ids = session.execute(agents_stmt).scalars().all()

        aggregates_created = 0
        bucket_size = "5m"

        for agent_id in agent_ids:
            # Aggregate CPU usage
            cpu_agg = session.execute(
                select(
                    func.min(MetricRecord.cpu_usage_percent),
                    func.max(MetricRecord.cpu_usage_percent),
                    func.avg(MetricRecord.cpu_usage_percent),
                    func.count(MetricRecord.id),
                ).where(
                    MetricRecord.agent_id == agent_id,
                    MetricRecord.timestamp >= window_start,
                )
            ).one()

            if cpu_agg[3] and cpu_agg[3] > 0:
                # Truncate timestamp to 5-minute bucket
                bucket_start = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)
                agg = MetricAggregate(
                    agent_id=agent_id,
                    metric_key="cpu.usage_percent",
                    dimension=None,
                    bucket_start=bucket_start,
                    bucket_size=bucket_size,
                    min_value=float(cpu_agg[0]),
                    max_value=float(cpu_agg[1]),
                    avg_value=float(cpu_agg[2]),
                    sample_count=int(cpu_agg[3]),
                )
                session.merge(agg)
                aggregates_created += 1

        session.commit()
        return {"aggregates_created": aggregates_created}
