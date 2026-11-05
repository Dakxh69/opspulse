"""
OpsPulse Agent — Tests: API Client & Retries
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from opspulse_agent.client.api_client import OpsPulseApiClient
from opspulse_agent.config import BackendSettings
from opspulse_agent.payload import MetricBatch, MetricSample


def test_api_client_heartbeat_success() -> None:
    """Verifies successful heartbeat returns True."""
    settings = BackendSettings(
        base_url="http://localhost:8000", agent_id="agent-1", agent_secret="sec-1"
    )
    client = OpsPulseApiClient(settings)

    mock_resp = MagicMock()
    mock_resp.status_code = 204

    with patch.object(httpx.Client, "post", return_value=mock_resp):
        success = client.send_heartbeat()
        assert success is True
    client.close()


def test_api_client_heartbeat_transport_failure() -> None:
    """Verifies connection failure returns False safely."""
    settings = BackendSettings(base_url="http://localhost:8000")
    client = OpsPulseApiClient(settings)

    with patch.object(httpx.Client, "post", side_effect=httpx.ConnectError("Connection refused")):
        success = client.send_heartbeat()
        assert success is False
    client.close()


def test_api_client_send_metrics_success() -> None:
    """Verifies successful batch submission."""
    settings = BackendSettings(base_url="http://localhost:8000")
    client = OpsPulseApiClient(settings)

    batch = MetricBatch(agent_id="agent-1", metrics=[MetricSample()])
    mock_resp = MagicMock()
    mock_resp.status_code = 202

    with patch.object(httpx.Client, "post", return_value=mock_resp):
        success = client.send_metrics(batch)
        assert success is True
    client.close()


def test_api_client_send_metrics_retry_on_server_error() -> None:
    """Verifies transient 500 error triggers backoff retry and succeeds on subsequent try."""
    settings = BackendSettings(base_url="http://localhost:8000")
    client = OpsPulseApiClient(settings)

    batch = MetricBatch(agent_id="agent-1", metrics=[MetricSample()])
    resp_fail = MagicMock()
    resp_fail.status_code = 503

    resp_ok = MagicMock()
    resp_ok.status_code = 202

    with (
        patch.object(httpx.Client, "post", side_effect=[resp_fail, resp_ok]),
        patch("time.sleep", return_value=None),  # Fast test execution
    ):
        success = client.send_metrics(batch, max_retries=2, base_delay_seconds=0.01)
        assert success is True
    client.close()


def test_api_client_send_metrics_client_error_no_retry() -> None:
    """Verifies 401/422 client errors fail immediately without pointless retries."""
    settings = BackendSettings(base_url="http://localhost:8000")
    client = OpsPulseApiClient(settings)

    batch = MetricBatch(agent_id="agent-1", metrics=[MetricSample()])
    resp_401 = MagicMock()
    resp_401.status_code = 401

    with (
        patch.object(httpx.Client, "post", return_value=resp_401) as mock_post,
        patch("time.sleep") as mock_sleep,
    ):
        success = client.send_metrics(batch, max_retries=3)
        assert success is False
        assert mock_post.call_count == 1
        assert mock_sleep.call_count == 0
    client.close()
