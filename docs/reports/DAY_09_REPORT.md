# Day 09 Report: Heartbeat & Metric Ingestion API

**Date:** 2026-11-05  
**Phase:** Phase 3 — Identity and Ingestion  
**Status:** Completed  

---

## 1. Executive Summary
Day 9 establishes the real-time ingestion interface between monitored hosts and the OpsPulse backend. Monitored nodes transmit periodic liveness pings and batched telemetry. We implemented the heartbeat endpoint with caller authentication, timestamp updates, and automatic status transitions, as well as the metric ingestion endpoint with request payload validation matching the agent's schema, agent identity verification to prevent spoofing, and bounded batch limits.

---

## 2. Features Completed
1. **Agent Heartbeat (`POST /api/v1/agents/heartbeat`):**
   - Secured with `get_current_agent` dependency (`X-Agent-ID` and `X-Agent-Secret`).
   - Updates `agent.last_heartbeat` with the current UTC timestamp and confirms `agent.status = AgentStatus.ONLINE`.
   - Returns standard HTTP 204 No Content.
2. **Metric Telemetry Ingestion Schemas (`app/schemas/metrics.py`):**
   - Mirrored agent schema: `CpuMetrics`, `CpuFrequency`, `CpuLoadAverage`, `MemoryMetrics`, `SwapMetrics`, `DiskItem`, `NetworkInterfaceItem`, `MetricSample`, and `MetricBatch`.
   - Structural validation enforcing:
     - `usage_percent` boundaries (0.0 to 100.0).
     - Byte counters and rates non-negative (>= 0).
     - Batch sizes strictly bounded (`min_length=1`, `max_length=100`).
3. **Metric Ingestion Endpoint (`POST /api/v1/metrics/ingest`):**
   - Authenticated with `get_current_agent`.
   - Identity verification: validates that `batch.agent_id` strictly matches the caller's authenticated `current_agent.id`, returning HTTP 400 Bad Request on mismatch (spoofing protection).
   - Returns HTTP 202 Accepted with `IngestionResponse(status="accepted", batch_id, samples_received)`.

---

## 3. Technical Architecture & Decisions
- **DEC-016: Agent Identity Anti-Spoofing Check:**
  - *Context:* Even if an agent has valid credentials, a compromised agent could attempt to submit telemetry claiming to originate from a different host UUID.
  - *Decision:* `POST /api/v1/metrics/ingest` compares `batch.agent_id` with `str(current_agent.id)`. Any divergence immediately aborts the ingestion with HTTP 400 Bad Request.
- **DEC-017: Bounded Batch Size Enforcement:**
  - *Context:* Unbounded ingestion arrays allow bad actors or misconfigured agents to cause memory exhaustion (DoS).
  - *Decision:* `MetricBatch.metrics` enforces `min_length=1` and `max_length=100`. Requests violating these constraints are rejected at the Pydantic validation boundary with HTTP 422 Unprocessable Entity.

---

## 4. Verification & Testing Evidence
- **Backend Test Suite (Dockerized):**
  - Ran `pytest -v tests/test_ingest_api.py`:
    - `test_heartbeat_lifecycle PASSED` (covers 401 unauth, 401 bad secret, 204 success, DB state verification).
    - `test_metrics_ingest_success PASSED` (covers complete multi-collector payload, 202 response).
    - `test_metrics_ingest_spoofed_agent_id_rejected PASSED` (verifies 400 rejection).
    - `test_metrics_ingest_empty_batch_rejected PASSED` (verifies 422 boundary rejection).
  - Ran full test suite: 20 passing tests.
- **Agent Test Suite (Host Linux):**
  - 31 passing tests.
- **Static Analysis & Formatting:**
  - `ruff check app tests`: All checks passed.
  - `ruff format --check app tests`: 42 files properly formatted.
  - `mypy app`: Success (0 issues found across 34 source files).

---

## 5. Known Issues & Mitigations
- None.

---

## 6. Next Steps (Day 10)
- Configure Redis and Celery for asynchronous background processing.
- Create `processed_batches` model and database migration for task deduplication and worker idempotency (Section 17.9).
- Implement `process_metric_batch` worker task.
- Wire `POST /api/v1/metrics/ingest` to publish tasks to Redis and return 202 Accepted (503 if Redis is unreachable).

