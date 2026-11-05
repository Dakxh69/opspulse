# Day 08 Report: Agent Provisioning, User Authentication, RBAC & Audit Trail

**Date:** 2026-11-05  
**Phase:** Phase 3 — Identity and Ingestion  
**Status:** Completed  

---

## 1. Executive Summary
Day 8 delivers the identity and access management backbone for OpsPulse. Monitored Linux hosts require secure provisioning and authentication before transmitting metric streams, and dashboard users require role-based access control (Admin, Operator, Viewer). Today we implemented JWT-based authentication using secure HttpOnly cookies, agent provisioning with high-entropy 64-character secrets and bcrypt hashing, credential rotation and revocation flows, an append-only audit trail capturing security-critical events (spec Section 17.10), and a CLI bootstrap command for the initial system administrator.

---

## 2. Features Completed
1. **User Authentication & RBAC (`app/api/v1/auth.py`, `app/api/deps.py`):**
   - `POST /api/v1/auth/login`: Authenticates user credentials via native bcrypt verification; returns user profile and sets an `access_token` HttpOnly cookie.
   - `POST /api/v1/auth/logout`: Clears session cookie and writes a `USER_LOGOUT` audit log entry.
   - `GET /api/v1/auth/me`: Validates session cookie or Bearer token; retrieves current user profile.
   - `POST /api/v1/auth/register`: Admin-only endpoint allowing administrators to create accounts and assign roles (`ADMIN`, `OPERATOR`, `VIEWER`).
2. **User Management (`app/api/v1/users.py`):**
   - `GET /api/v1/users`: Admin-only listing of all system users.
   - `GET /api/v1/users/{id}`: Detailed user retrieval.
   - `PATCH /api/v1/users/{id}`: Modifies user role or deactivates account (with safety guard preventing self-deactivation).
3. **Agent Provisioning & Lifecycle (`app/api/v1/agents.py`):**
   - `POST /api/v1/agents/register`: Generates a cryptographically secure 64-character token (`secrets.token_hex(32)`), stores the bcrypt hash in PostgreSQL, and returns the plaintext secret key strictly once.
   - `GET /api/v1/agents`: Lists monitored hosts without leaking credential hashes or secrets.
   - `GET /api/v1/agents/{id}`: Agent detail retrieval.
   - `PATCH /api/v1/agents/{id}`: Agent metadata updates.
   - `POST /api/v1/agents/{id}/rotate-credential`: Generates a new secret token, updates the bcrypt hash, and invalidates previous credentials immediately.
   - `DELETE /api/v1/agents/{id}`: Revokes agent credential (`revoked_at` timestamp), transitions status to `OFFLINE`, and causes subsequent agent calls to be rejected.
4. **Agent Authentication Dependency (`get_current_agent` in `app/api/deps.py`):**
   - Authenticates agent requests using `X-Agent-ID` and `X-Agent-Secret` headers against PostgreSQL bcrypt hashes.
   - Rejects unauthenticated, invalid, or revoked agents.
5. **Audit Logging Subsystem (`app/models/audit.py`, `app/services/audit_service.py`, `app/api/v1/audit.py`):**
   - PostgreSQL `audit_logs` table with indexed action, actor, target, and UTC timestamps (Alembic migration `8d5340076971`).
   - Service helper `record_audit_log` with automatic transaction commit to preserve audit records even during 4xx/5xx HTTP exceptions.
   - `GET /api/v1/audit-logs`: Admin-only paginated endpoint supporting multi-attribute filtering (actor, action, target type/id, timestamp range).
6. **CLI Initial Admin Seed (`app/cli.py`):**
   - `python -m app.cli seed-admin`: Reads `FIRST_ADMIN_EMAIL` and `FIRST_ADMIN_PASSWORD` from environment variables, verifies minimum password strength, and idempotently creates the initial administrator.

---

## 3. Technical Architecture & Decisions
- **DEC-013: Direct Bcrypt Hashing over Deprecated Passlib:**
  - *Context:* Upstream `passlib` is unmaintained and incompatible with `bcrypt >= 4.1.0` due to internal `__about__` version detection bugs that erroneously trigger 72-byte truncation assertions on modern Python runtimes.
  - *Decision:* Use standard, native `bcrypt` (`hashpw`/`checkpw`) directly in `app/core/security.py`. All inputs are explicitly encoded to UTF-8 and bounded to 72 bytes.
- **DEC-014: HttpOnly Session Cookies with Bearer Fallback:**
  - *Context:* Storing JWT tokens in browser `localStorage` exposes user sessions to Cross-Site Scripting (XSS) token theft.
  - *Decision:* Login issues an `HttpOnly` cookie with `SameSite=Strict`. For headless API or CLI clients, `app/api/deps.py` also checks the `Authorization: Bearer <token>` header as a secondary fallback.
- **DEC-015: Guaranteed Audit Persistence on Failure:**
  - *Context:* Standard database sessions rollback uncommitted changes when an `HTTPException` is raised. A failed login attempt or unauthorized action would therefore have its audit record discarded if not committed immediately.
  - *Decision:* `record_audit_log` commits immediately upon recording security-relevant events, ensuring an immutable log even when request processing aborts with an HTTP error.

---

## 4. Verification & Testing Evidence
- **Backend Test Suite (Dockerized):**
  - Ran `pytest -v` inside `opspulse-backend:test`:
  - `tests/test_agents.py::test_agent_provisioning_and_rotation_flow PASSED`
  - `tests/test_audit.py::test_audit_logs_endpoint_rbac PASSED`
  - `tests/test_audit.py::test_cli_seed_admin PASSED`
  - `tests/test_auth.py::test_login_success_and_sets_cookie PASSED`
  - `tests/test_auth.py::test_login_invalid_password PASSED`
  - `tests/test_auth.py::test_auth_me_authenticated_and_unauthenticated PASSED`
  - `tests/test_auth.py::test_logout_clears_cookie PASSED`
  - `tests/test_auth.py::test_register_user_admin_only PASSED`
  - `tests/test_database.py` (4 tests) `PASSED`
  - `tests/test_health.py` (4 tests) `PASSED`
  - **Result:** 16 tests passed in 7.09s.
- **Agent Test Suite (Host Linux):**
  - Ran `cd agent && .venv/bin/pytest -v`:
  - **Result:** 31 tests passed in 0.39s.
- **Static Analysis & Formatting:**
  - `ruff check app tests`: 0 errors.
  - `mypy app`: Success (0 issues found across 32 source files).

---

## 5. Known Issues & Mitigations
- None. All security and identity endpoints behave according to specification.

---

## 6. Next Steps (Day 9)
- Implement backend metric schemas mirroring the agent payload (`MetricSampleSchema`, `MetricBatchSchema`, `IngestionResponse`).
- Implement `POST /api/v1/agents/heartbeat` with `get_current_agent` dependency and timestamp updates.
- Implement `POST /api/v1/metrics/ingest` with request body size enforcement and schema validation.
- Unit and integration tests for Day 9.

