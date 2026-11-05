"""
OpsPulse Host Monitoring Agent — Backend API Client

Handles authenticated communication with the FastAPI backend:
- Heartbeat pings (POST /api/v1/agents/heartbeat)
- Metric batch ingestion (POST /api/v1/metrics/ingest)
- Exponential backoff with random jitter on network failures
- Never logs plaintext credentials
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

from opspulse_agent.config import BackendSettings
from opspulse_agent.payload import MetricBatch

logger = logging.getLogger(__name__)


class OpsPulseApiClient:
    """HTTP client communicating with the OpsPulse ingestion API."""

    def __init__(self, backend_settings: BackendSettings) -> None:
        self.settings = backend_settings
        self.base_url = backend_settings.base_url.rstrip("/")
        self._client: httpx.Client | None = None

    def _get_headers(self) -> dict[str, str]:
        """Builds authenticated request headers."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.settings.agent_id:
            headers["X-Agent-ID"] = self.settings.agent_id
        if self.settings.agent_secret:
            headers["X-Agent-Secret"] = self.settings.agent_secret
        return headers

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.settings.timeout_seconds,
                headers=self._get_headers(),
            )
        return self._client

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self._client is not None and not self._client.is_closed:
            self._client.close()
            self._client = None

    def send_heartbeat(self) -> bool:
        """
        Sends an authenticated heartbeat ping to the backend.
        Returns True if accepted (HTTP 200 or 204), False otherwise.
        """
        client = self._get_client()
        try:
            response = client.post("/api/v1/agents/heartbeat")
            if response.status_code in {200, 204}:
                logger.debug("Heartbeat ping acknowledged")
                return True
            logger.warning(
                "Heartbeat rejected by backend",
                extra={"status_code": response.status_code},
            )
            return False
        except httpx.TransportError as exc:
            logger.warning("Heartbeat failed to reach backend", extra={"error": str(exc)})
            return False

    def send_metrics(
        self,
        batch: MetricBatch,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 15.0,
    ) -> bool:
        """
        Sends a batch of metric samples to POST /api/v1/metrics/ingest.
        Retries transient network or 5xx errors using exponential backoff with jitter.
        Returns True if accepted (HTTP 200 or 202), False otherwise.
        """
        client = self._get_client()
        payload_data: dict[str, Any] = batch.model_dump(mode="json")

        for attempt in range(max_retries + 1):
            try:
                response = client.post("/api/v1/metrics/ingest", json=payload_data)

                # HTTP 200 OK or 202 Accepted indicates successful ingestion
                if response.status_code in {200, 202}:
                    logger.debug("Metric batch accepted", extra={"batch_id": batch.batch_id})
                    return True

                # If 4xx client error (e.g. 401 unauthorized or 422 invalid payload), do not retry
                if 400 <= response.status_code < 500:
                    logger.error(
                        "Metric batch rejected by API with client error",
                        extra={"status_code": response.status_code, "batch_id": batch.batch_id},
                    )
                    return False

                # 5xx server error: transient; retry with backoff
                logger.warning(
                    "Metric batch received server error",
                    extra={"status_code": response.status_code, "attempt": attempt},
                )

            except httpx.TransportError as exc:
                logger.warning(
                    "Network error during metric ingestion",
                    extra={"error": str(exc), "attempt": attempt},
                )

            if attempt < max_retries:
                # Exponential backoff with random jitter
                backoff = min(max_delay_seconds, base_delay_seconds * (2**attempt))
                jitter = random.uniform(0.1, 0.5)
                sleep_duration = backoff + jitter
                time.sleep(sleep_duration)

        return False
