# Day 16 Report: Incident Lifecycle & State Machine

**Date:** 2026-11-05  
**Phase:** Phase 5 — Incidents and Agent Health  
**Status:** Completed  

---

## 1. Executive Summary
Day 16 implements the operational lifecycle state machine and REST endpoints for incident management per spec Section 13 and Section 18. Monitored incidents follow a strict lifecycle progression (`OPEN -> ACKNOWLEDGED -> INVESTIGATING -> RESOLVED -> CLOSED`), with support for reopening resolved incidents if issues recur. Every transition validates allowed paths, binds the actor identity, updates temporal tracking, writes an immutable timeline event, and records an audit log entry.

---

## 2. Features Completed
1. **Lifecycle State Transition Endpoints (`app/api/v1/incidents.py`):**
   - `POST /api/v1/incidents/{id}/acknowledge`: Transitions `OPEN` or `INVESTIGATING` to `ACKNOWLEDGED`. Sets `acknowledged_by_user_id` and appends `ACKNOWLEDGED` event. Admin & Operator only.
   - `POST /api/v1/incidents/{id}/resolve`: Transitions active incidents to `RESOLVED`. Sets `resolved_by_user_id`, `resolved_at`, and appends `RESOLVED` event. Admin & Operator only.
   - `POST /api/v1/incidents/{id}/reopen`: Transitions `RESOLVED` or `CLOSED` incidents back to `OPEN`. Clears `resolved_at` and appends `REOPENED` event. Admin & Operator only.
   - `POST /api/v1/incidents/{id}/notes`: Appends investigation notes as `NOTE_ADDED` events with author attribution. Admin & Operator only.
2. **Read & Detail Endpoints:**
   - `GET /api/v1/incidents`: Filter by `status`, `severity`, `agent_id`, and time range with pagination. Accessible to all authenticated users (Admin, Operator, Viewer).
   - `GET /api/v1/incidents/{id}`: Single incident detail with selectin-loaded event timeline.
   - `GET /api/v1/incidents/{id}/events`: Chronological list of events for the incident.
3. **Invalid State Transition Protection:**
   - Rejects invalid operations (e.g. attempting to acknowledge an already resolved incident) with 400 Bad Request.
4. **Audit Integration:**
   - Records `INCIDENT_ACKNOWLEDGE`, `INCIDENT_RESOLVE`, and `INCIDENT_REOPEN` in the immutable `audit_logs` table.

---

## 3. Technical Architecture & Decisions
- **DEC-028: State Machine Transition Enforcement:**
  - *Context:* Arbitrary state jumps (e.g. acknowledging after resolution) create corrupt incident histories.
  - *Decision:* Endpoints explicitly validate the starting state before mutating, ensuring lifecycle integrity and proper attribution.

---

## 4. Verification & Testing Evidence
- **Backend Tests (`backend/tests/test_incidents.py`):**
  - `test_list_and_filter_incidents PASSED`: Verified listing, filtering by status/severity, and Viewer read-only access.
  - `test_get_incident_detail PASSED`: Verified detail retrieval and 404 for nonexistent UUID.
  - `test_incident_lifecycle_and_rbac PASSED`: Verified full transition flow (Viewer 403, Operator acknowledge, note addition, resolution, invalid transition rejection with 400, reopening, and timeline ordering).

---

## 5. Next Steps
- Day 17: Agent health monitoring and offline detection.
