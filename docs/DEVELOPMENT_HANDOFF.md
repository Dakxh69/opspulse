# OpsPulse — Development Handoff

> Update at the end of every session. Enables any AI or human developer to resume accurately.
> Never store passwords, API keys, secrets, or private keys here.

---

## Handoff: Session 6 (Day 12 Complete — Phase 4 In Progress)
**Date:** 2026-11-05  
**Current State:** Phase 1, Phase 2, and Phase 3 are 100% complete. Phase 4 is 50% complete (Days 11 and 12 done). Ready for Day 13 (Alert Evaluation).

### Repository Location
`/home/daxx69/.gemini/antigravity/scratch/opspulse`  
**Branch:** `main`  

### Current Day and Phase
- **Day:** 12 of 30 complete (Alert-Rule Management)
- **Phase:** Phase 4 — Storage and Alerts (In Progress — 50%)
- **Roadmap Position:** Day 13 next (Alert Evaluation Engine)

### Verified Completed Work
- [x] Host environment audited (Ubuntu 26.04.1, Docker 29, Docker Compose v5.6.0)
- [x] Monorepo scaffolded per spec Section 19 on `main` branch
- [x] Multi-stage Docker containerization using `python:3.12-slim` with `/opt/venv`
- [x] FastAPI application factory with async lifespan, CORS, and typed settings
- [x] PostgreSQL 17 Alpine healthy in Docker Compose
- [x] Redis 7 Alpine healthy in Docker Compose
- [x] Dual-engine SQLAlchemy setup (asyncpg for API, psycopg2 for Celery workers & migrations)
- [x] Complete Linux Host Monitoring Agent (`opspulse_agent`):
  - CPU collector (non-blocking delta sampling, multi-core, loadavg)
  - Memory collector (RAM, swap, zero-swap support)
  - Disk collector (physical partitions, pseudo-fs filtering)
  - Network collector (counter deltas, rate calculations, counter reset handling)
  - Configuration loader (YAML & env overrides)
  - HTTP client with jittered exponential backoff retries
  - Scheduler with bounded ring buffer (100 samples) and graceful shutdown signal handlers
- [x] Identity & Provisioning (Day 8):
  - User authentication via HttpOnly SameSite=Strict cookies with Bearer fallback
  - Native Bcrypt hashing
  - Agent token generation (64-char hex) and rotation/revocation
  - CLI initial admin bootstrap (`python -m app.cli seed-admin`)
  - Security audit trail table (`audit_logs`) with immediate commit persistence
- [x] Ingestion & Heartbeat (Day 9):
  - `POST /api/v1/agents/heartbeat` (204 No Content, updates status to ONLINE)
  - `POST /api/v1/metrics/ingest` (202 Accepted, anti-spoofing identity validation)
  - Batch size enforcement (1 to 100 samples)
- [x] Queue & Worker Pipeline (Day 10):
  - Celery worker configured with Redis broker
  - Deduplication table (`processed_batches`) with unique constraint on `(agent_id, batch_id)`
  - Task `process_metric_batch` with automatic retry backoff and idempotency handling
  - 503 Service Unavailable returned when queue broker is disconnected
- [x] Metric Persistence & Maintenance (Day 11):
  - Normalized relational schema (`metric_records`, `metric_disks`, `metric_networks`) with CASCADE deletion
  - Downsampled aggregate table (`metric_aggregates`)
  - Query endpoints: `GET /metrics/{agent_id}`, `/latest`, `/summary`
  - Retention cleanup task (`cleanup_old_metrics`) and downsampling task (`downsample_metrics`)
- [x] Alert-Rule Management (Day 12):
  - `AlertRule` model, migration `d21a482937e2`
  - CRUD REST endpoints (`POST`, `GET`, `PATCH`, `DELETE /api/v1/alerts/rules`)
  - Role-based authorization (Admin/Operator write, Viewer read)
  - Audit log entries on rule creation, modification, deletion
- [x] 59/59 automated tests passing (28 backend in Docker + 31 agent on host)
- [x] Static analysis clean: Ruff (0 errors across 52 backend + 15 agent files), Mypy strict (0 errors in 41 backend files + agent)

### Incomplete Work (Target: Days 13–18)
- [ ] Alert evaluation engine in Celery/Worker with sliding windows (Day 13)
- [ ] Alert reliability: sustained breaches, cooldown suppression, auto-clearing (Day 14)
- [ ] Incident creation & deduplication state machine (Day 15)
- [ ] Incident lifecycle endpoints: acknowledge, resolve, reopen, notes (Day 16)
- [ ] Agent health evaluator & offline detection (Day 17)
- [ ] Frontend setup with Vite, React, Tailwind CSS (Day 18)

### Latest Test State
- **Automated Tests:** 59 passed (28 backend in Docker + 31 agent on host)
- **Linter / Formatter:** 0 errors across all source files (`ruff check`, `ruff format --check`)
- **Type Checker:** 0 errors across all source files (`mypy`)

### Active Issues
- None.

### Recent Decisions
- DEC-013: Direct Bcrypt hashing over deprecated passlib.
- DEC-014: HttpOnly session cookies with Bearer fallback.
- DEC-015: Guaranteed audit persistence on failure.
- DEC-016: Agent identity anti-spoofing check.
- DEC-017: Bounded batch size enforcement.
- DEC-018: Kombu & Redis version pinning (`kombu==5.4.2`, `redis==5.2.0`).
- DEC-019: 503 Service Unavailable on queue failure.
- DEC-020: Relational normalization with ON DELETE CASCADE.
- DEC-021: Idempotent metric downsampling with `NULLS NOT DISTINCT`.
- DEC-022: Role-based access for alert rule management (Admin & Operator write, Viewer read).
- DEC-023: Alert rule auditability.

### Exact Commands to Resume Testing
```bash
# Agent tests
cd /home/daxx69/.gemini/antigravity/scratch/opspulse/agent && .venv/bin/pytest -v

# Backend tests
cd /home/daxx69/.gemini/antigravity/scratch/opspulse && docker run --rm --network opspulse_default -e POSTGRES_HOST=opspulse-postgres -e POSTGRES_PASSWORD=CHANGE_ME -e REDIS_HOST=opspulse-redis -e TESTING=true -v $(pwd)/backend:/app opspulse-backend:test pytest -v
```

### Exact Next Task
Day 13 — Alert Evaluation: Implement the evaluation engine in Celery worker that checks newly ingested metric batches against enabled alert rules, evaluating sliding windows and consecutive breach counters.
