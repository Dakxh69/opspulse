"""
OpsPulse Host Monitoring Agent — Agent Scheduler & Runtime Loop

Coordinates:
- Periodic metric collection ticks.
- Bounded local FIFO queue (collections.deque) for offline resilience.
- Periodic heartbeat pings to the central API.
- Flushes buffered batches upon backend recovery.
- Graceful shutdown on SIGTERM / SIGINT signals.
"""

from __future__ import annotations

import collections
import logging
import signal
import time
from types import FrameType

from opspulse_agent.client.api_client import OpsPulseApiClient
from opspulse_agent.collectors.cpu import CpuCollector
from opspulse_agent.collectors.disk import DiskCollector
from opspulse_agent.collectors.memory import MemoryCollector
from opspulse_agent.collectors.network import NetworkCollector
from opspulse_agent.config import AgentConfig
from opspulse_agent.payload import MetricBatch, MetricSample

logger = logging.getLogger(__name__)


class AgentScheduler:
    """Runtime orchestrator executing periodic collection and transmission."""

    def __init__(self, config: AgentConfig, api_client: OpsPulseApiClient | None = None) -> None:
        self.config = config
        self.api_client = api_client or OpsPulseApiClient(config.backend)

        # Initialize telemetry collectors based on feature configuration
        self.cpu_collector = CpuCollector() if config.features.cpu else None
        self.memory_collector = MemoryCollector() if config.features.memory else None
        self.disk_collector = DiskCollector() if config.features.disk else None
        self.network_collector = NetworkCollector() if config.features.network else None

        # Bounded local buffer to prevent memory exhaustion during extended backend outages
        self.buffer: collections.deque[MetricBatch] = collections.deque(
            maxlen=config.agent.local_buffer_max_batches
        )
        self.current_samples: list[MetricSample] = []

        self._running = False
        self._last_collection_time = 0.0
        self._last_heartbeat_time = 0.0

    def collect_sample(self) -> MetricSample:
        """Sample all active collectors and assemble a MetricSample."""
        return MetricSample(
            cpu=self.cpu_collector.collect() if self.cpu_collector else None,
            memory=self.memory_collector.collect() if self.memory_collector else None,
            disks=self.disk_collector.collect() if self.disk_collector else [],
            networks=self.network_collector.collect() if self.network_collector else [],
        )

    def tick_collection(self) -> None:
        """Executes a single collection cycle and flushes to buffer if batch is full."""
        sample = self.collect_sample()
        self.current_samples.append(sample)

        # When current batch reaches configured batch_size, enqueue it
        if len(self.current_samples) >= self.config.agent.batch_size:
            agent_id = self.config.backend.agent_id or "unregistered-agent"
            batch = MetricBatch(
                agent_id=agent_id,
                metrics=list(self.current_samples),
            )
            self.buffer.append(batch)
            self.current_samples.clear()
            logger.debug(
                "Enqueued metric batch",
                extra={"batch_id": batch.batch_id, "buffer_depth": len(self.buffer)},
            )

    def flush_buffer(self) -> int:
        """
        Attempts to deliver all queued batches in FIFO order.
        Returns the number of batches successfully sent.
        """
        sent_count = 0
        while self.buffer:
            batch = self.buffer[0]
            success = self.api_client.send_metrics(batch)
            if success:
                self.buffer.popleft()
                sent_count += 1
            else:
                # Backend is unavailable or batch rejected; keep remaining in buffer
                break
        return sent_count

    def tick_heartbeat(self) -> bool:
        """Sends periodic heartbeat ping if interval has elapsed."""
        now = time.monotonic()
        if now - self._last_heartbeat_time >= self.config.backend.heartbeat_interval_seconds:
            self._last_heartbeat_time = now
            return self.api_client.send_heartbeat()
        return False

    def handle_shutdown(self, signum: int, frame: FrameType | None) -> None:
        """Signal handler triggering graceful shutdown."""
        logger.info("Shutdown signal received", extra={"signal": signum})
        self._running = False

    def register_signal_handlers(self) -> None:
        """Registers SIGINT and SIGTERM handlers."""
        try:
            signal.signal(signal.SIGINT, self.handle_shutdown)
            signal.signal(signal.SIGTERM, self.handle_shutdown)
        except (ValueError, AttributeError):
            # Not in main thread or unsupported platform
            pass

    def run_once(self) -> None:
        """Performs a single iteration of collection, heartbeat, and buffer flushing."""
        now = time.monotonic()
        if now - self._last_collection_time >= self.config.agent.collection_interval_seconds:
            self._last_collection_time = now
            self.tick_collection()
            self.flush_buffer()

        self.tick_heartbeat()

    def run(self) -> None:
        """Starts the agent runtime loop."""
        self._running = True
        self.register_signal_handlers()
        logger.info(
            "OpsPulse monitoring agent running",
            extra={"agent_name": self.config.agent.name},
        )

        try:
            while self._running:
                self.run_once()
                # Sleep briefly to avoid 100% CPU busy-looping while remaining responsive to shutdown
                time.sleep(0.5)
        finally:
            logger.info("Agent shutting down; attempting final buffer flush")
            # If any remaining samples are unbatched, create final batch
            if self.current_samples:
                agent_id = self.config.backend.agent_id or "unregistered-agent"
                self.buffer.append(
                    MetricBatch(agent_id=agent_id, metrics=list(self.current_samples))
                )
                self.current_samples.clear()
            self.flush_buffer()
            self.api_client.close()
            logger.info("Agent shutdown complete")
