# Day 13 Report: Alert Evaluation Engine

**Date:** 2026-11-05  
**Phase:** Phase 4 — Storage and Alerts  
**Status:** Completed  

---

## 1. Executive Summary
Day 13 implements the core alert evaluation engine for OpsPulse per spec Section 12. Alert rules must not merely trigger on arbitrary raw spikes; real-world infrastructure monitoring requires operator-defined evaluation windows, consecutive sustained breach criteria (to filter out transient jitter), multi-dimensional aggregation (EACH partition vs MAX usage across interfaces), and explicit differentiation between zero values and missing telemetry data. We implemented `app/services/alert_engine.py` and integrated it directly into the worker pipeline and query layer.

---

## 2. Features Completed
1. **Operator Evaluation Matrix (`evaluate_operator`):**
   - Precise arithmetic evaluation for comparison operators: `>`, `>=`, `<`, `<=`, `==`.
   - Floating point epsilon handling for equality comparisons (`1e-5`).
2. **Consecutive Breach & Window Logic:**
   - Filters metric observations strictly within `rule.evaluation_window_seconds`.
   - Requires at least `rule.consecutive_breaches` sustained samples breaching the threshold consecutively.
   - Prevents transient single-sample spikes from triggering spurious alerts (e.g., an 85% CPU sample surrounded by 60% and 55% will not trip a 3-consecutive-sample rule).
3. **Missing Data vs Zero Value Handling:**
   - Missing data (empty window, absent disk partition, uncollected network counter) returns `None` rather than `0.0`.
   - Prevents `<` operators from tripping falsely on missing metrics.
4. **Dimension Filtering and Aggregation (`EACH` vs `MAX`):**
   - Explicit `dimension_filter` (e.g. `/data` mount point) isolates the target filesystem.
   - `DimensionAggregation.EACH` evaluates each mounted disk or network interface independently.
   - `DimensionAggregation.MAX` computes the peak value across all interfaces/mounts per sample.

---

## 3. Technical Architecture & Decisions
- **DEC-024: Window-Based Sample Evaluation in Transactional Pipeline:**
  - *Context:* Metric evaluation must observe temporal trends across recent samples, not just the latest single sample.
  - *Decision:* The Alert Engine queries recent samples within `evaluation_window_seconds` from PostgreSQL with `selectinload` for child disk/network entities, ensuring full dimension fidelity without N+1 query overhead.

---

## 4. Verification & Testing Evidence
- **Backend Tests (`backend/tests/test_alert_evaluation.py`):**
  - `test_operator_evaluation PASSED`: Verified `>`, `>=`, `<`, `<=`, and `==`.
  - `test_consecutive_breaches_and_transient_spikes PASSED`: Demonstrated transient spike suppression and sustained breach firing.
  - `test_missing_data_behavior PASSED`: Missing metrics verified not to evaluate as zero.
  - `test_dimension_filter_and_aggregation PASSED`: Verified independent disk evaluation.

---

## 5. Next Steps
- Day 14: Alert reliability, cooldown suppression, active incident deduplication, and auto-resolution.
