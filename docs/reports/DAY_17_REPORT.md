# Day 17 Report: Agent Health Monitoring & Offline Detection

**Date:** 2026-11-05  
**Phase:** Phase 5 — Incidents and Agent Health  
**Status:** Completed  

---

## 1. Executive Summary
Day 17 implements automated agent availability monitoring and offline incident generation per spec Section 14. In distributed environments, host monitoring agents can crash, freeze, lose network connectivity, or be powered off. OpsPulse monitors heartbeat freshness through a Celery background task (`monitor_agent_health`), transitions agent states (`ONLINE -> DEGRADED -> OFFLINE`), creates deduplicated "Agent Offline" critical incidents, and auto-recovers back to `ONLINE` with incident resolution when heartbeats resume.

---

## 2. Features Completed
1. **Heartbeat Freshness Evaluation Task (`app/workers/tasks.monitor_agent_health`):**
   - Configurable thresholds via `Settings`:
     - `AGENT_DEGRADED_AFTER_SECONDS`: 60s (status becomes `DEGRADED`).
     - `AGENT_OFFLINE_AFTER_SECONDS`: 120s (status becomes `OFFLINE`).
   - Ignores revoked/decommissioned agents.
2. **Deduplicated Offline Incident Management:**
   - When an agent exceeds 120s without a heartbeat, checks for an existing active offline incident (`dimension="heartbeat"`).
   - If not present: creates a `CRITICAL` incident titled `Agent Offline: <hostname>` with `DETECTED` event.
   - If already present: updates `last_seen_at` without spamming duplicate incidents on subsequent check intervals.
3. **Heartbeat Auto-Recovery (`app/api/v1/agents.py`):**
   - When an offline or degraded agent pings `POST /api/v1/agents/heartbeat`, its status transitions back to `ONLINE`.
   - Any active offline incidents are automatically resolved (`RESOLVED` status with `AUTO_CLEARED` event "Agent resumed heartbeat").

---

## 3. Technical Architecture & Decisions
- **DEC-029: Asynchronous Heartbeat Health Monitor with Heartbeat-Triggered Clearance:**
  - *Context:* Detecting missing heartbeats requires a periodic background evaluation, whereas detecting recovery can happen immediately when an incoming HTTP ping arrives.
  - *Decision:* Degradation and offline transitions are driven asynchronously by Celery task `monitor_agent_health`, while recovery happens synchronously inside `POST /api/v1/agents/heartbeat` for sub-second incident resolution.

---

## 4. Verification & Testing Evidence
- **Backend Tests (`backend/tests/test_agent_health.py`):**
  - `test_agent_health_state_transitions_and_deduplication PASSED`: Verified transitions from ONLINE -> DEGRADED (>60s) -> OFFLINE (>120s), creation of critical offline incident, and incident deduplication across repeated task executions.
  - `test_agent_auto_recovery_on_heartbeat PASSED`: Verified agent returning from offline status back to ONLINE via `POST /api/v1/agents/heartbeat` and verified automatic resolution with `AUTO_CLEARED` event.

---

## 5. Next Steps
- Day 18: Frontend setup, React 18, Vite, Tailwind CSS, and dashboard layout.
