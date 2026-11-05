# Day 14 Report: Alert Reliability & Deduplication

**Date:** 2026-11-05  
**Phase:** Phase 4 — Storage and Alerts  
**Status:** Completed  

---

## 1. Executive Summary
Day 14 delivers reliability, noise reduction, and lifecycle convergence for the Alert Engine per spec Section 12.3. Unmanaged alert systems suffer from notification storms, duplicate incident creation across scheduler ticks, flapping between breach and normal states, and stale unresolved issues. Day 14 implements active incident deduplication, post-resolution cooldown periods, auto-resolution with timeline event records when conditions normalize, and worker integration in Celery `process_metric_batch`.

---

## 2. Features Completed
1. **Incident Deduplication:**
   - Evaluates active incidents matching `(agent_id, rule_id, dimension)` where `status in [OPEN, ACKNOWLEDGED, INVESTIGATING]`.
   - When an ongoing breach is detected, does not create duplicate incidents; updates `last_seen_at = now` and flushes state.
2. **Cooldown Suppression:**
   - Configurable per-rule `cooldown_seconds` (default 300s).
   - Prevents flapping: when an incident is recently resolved, subsequent breaches within the cooldown period are suppressed, preventing alert noise.
3. **Auto-Resolution on Metric Normalization:**
   - When a monitored metric for an active incident returns within acceptable thresholds, the incident status transitions automatically to `RESOLVED` with `resolved_at = now`.
   - Records an `AUTO_CLEARED` event in the incident timeline detailing the normalized metric value.
4. **Celery Worker Pipeline Integration:**
   - Hooked `AlertEngine.evaluate_agent` into `process_metric_batch` in `app/workers/tasks.py`.
   - Persisted metric batches immediately trigger evaluation within the same worker context.

---

## 3. Technical Architecture & Decisions
- **DEC-025: Compound Active Index for Incident Deduplication:**
  - *Context:* Checking whether an active incident exists for an agent and rule must be sub-millisecond fast.
  - *Decision:* Created compound B-tree index `ix_incidents_active_lookup` on `(agent_id, rule_id, dimension, status)` to make deduplication lookups instant.
- **DEC-026: Automatic Clear Tracking:**
  - *Context:* Operators need to know whether an issue was manually resolved or self-healed by the infrastructure.
  - *Decision:* Auto-recovered incidents record an explicit `AUTO_CLEARED` timeline event with system actor (`actor_user_id=None`) and measured normal value.

---

## 4. Verification & Testing Evidence
- **Backend Tests (`backend/tests/test_alert_evaluation.py`):**
  - `test_deduplication_auto_resolution_and_cooldown PASSED`: Verified that ongoing breaches update `last_seen_at` without duplicating records, normalized metrics auto-resolve the incident with an `AUTO_CLEARED` event, and post-resolution spikes within cooldown are suppressed.

---

## 5. Next Steps
- Day 15 & Day 16: Incident creation, lifecycle state machine, and REST endpoints.

