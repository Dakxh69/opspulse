# Day 15 Report: Incident Creation & Database Models

**Date:** 2026-11-05  
**Phase:** Phase 5 — Incidents and Agent Health  
**Status:** Completed  

---

## 1. Executive Summary
Day 15 implements the database schema, relational structure, and creation services for operational incidents and timeline events per spec Section 13, 17.5, and 17.6. Incidents represent detected operational problems that demand human triage or automated intervention. We implemented the `Incident` and `IncidentEvent` database models, generated and applied Alembic migration `3e33c503e175`, and established relationships between incidents, agents, rules, and user assignees.

---

## 2. Features Completed
1. **Incident Database Model (`app/models/incident.py`):**
   - Table `incidents`: UUID primary key, `agent_id` foreign key (`CASCADE`), `rule_id` foreign key (`SET NULL`), optional `dimension` string.
   - Core metadata: `title`, `description`, `severity` (`alert_severity` enum), `status` (`incident_status` enum).
   - Temporal auditing: `first_detected_at`, `last_seen_at`, `resolved_at`.
   - Identity tracking: `acknowledged_by_user_id` and `resolved_by_user_id` foreign keys to `users.id`.
2. **Incident Event Database Model (`app/models/incident.py`):**
   - Table `incident_events`: UUID primary key, `incident_id` foreign key (`CASCADE`), `event_type` (`incident_event_type` enum).
   - Audit trail: `message` text, `actor_user_id` foreign key (`SET NULL`), `metadata` (`JSONB`), `created_at` timestamp.
   - Event types: `DETECTED`, `ACKNOWLEDGED`, `INVESTIGATING`, `NOTE_ADDED`, `RESOLVED`, `REOPENED`, `CLOSED`, `AUTO_CLEARED`.
3. **Database Migration (`3e33c503e175_create_incidents_and_events.py`):**
   - Created tables and compound indexes (`ix_incidents_active_lookup`, `ix_incidents_status_severity`).
   - Cleanly reused existing `alert_severity` PostgreSQL enum without collision.
4. **Pydantic Serialization Schemas (`app/schemas/incident.py`):**
   - `IncidentResponse`, `IncidentEventResponse`, `IncidentListResponse`, `IncidentNoteRequest`, `IncidentActionRequest`.

---

## 3. Technical Architecture & Decisions
- **DEC-027: Event-Sourced Incident History:**
  - *Context:* Compliance and post-mortem analysis require an immutable log of who took what action on an incident and when.
  - *Decision:* All state transitions, auto-clearances, and investigation notes are recorded as chronological `IncidentEvent` rows linked to the parent incident with cascading deletes.

---

## 4. Verification & Testing Evidence
- **Alembic Migration Verification:**
  - `alembic upgrade head` executed cleanly on PostgreSQL 17 container.
- **Relational Integrity Tests (`backend/tests/test_incidents.py`):**
  - Verified incident creation with associated `DETECTED` timeline event.

---

## 5. Next Steps
- Day 16: Incident lifecycle state machine, transitions, and API endpoints.
