# OpsPulse — Decision Log

> Record meaningful engineering decisions. Do not log trivial syntax choices.
> If a decision changes, add a new entry referencing the old ID. Never rewrite history.

---

## DEC-001 — Repository Strategy and Branch Naming
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Starting a new repository from scratch. Need to decide the initial branch name and structure.

### Decision
Use `main` as the default branch. Use a monorepo structure with `backend/`, `agent/`, `frontend/`, `simulator/`, and `docs/` as top-level directories, exactly matching spec Section 19.

### Alternatives Considered
1. Single `master` branch — Git legacy default; rejected in favour of modern `main`.
2. Separate repos per service — adds complexity without benefit at this scale; rejected.
3. Monorepo with `packages/` — unnecessary abstraction; spec layout is clear.

### Reason
The spec explicitly defines the directory layout. A monorepo makes it easy to run `docker compose` from the root, share configuration, and cross-reference backend and agent code. `main` is the modern default.

### Trade-offs
Monorepo means all code is in one place — simple to manage for a team of one, but would need a workspace tool (nx, turborepo) if the project scaled to many independent services. For this scale, plain monorepo is correct.

### Consequences
All Dockerfiles, Compose file, and CI reference paths from the monorepo root.

### Related Files
`.gitignore`, `docker-compose.yml`, `.github/workflows/`

---

## DEC-002 — Python Virtual Environment Strategy
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
The system Python 3.14.4 on Ubuntu 26.04 does not have `pip` installed at the system level (`python3 -m pip` returns "No module named pip"). We need a way to install Python packages for backend and agent development.

### Decision
Use `python3 -m venv <dir> --upgrade-deps` to create isolated virtual environments for `backend/` and `agent/`. This creates a venv with its own pip. All `requirements.txt` files are installed inside the venv. Docker images use `python3 -m venv` inside the container as well, or rely on the Docker base image having pip.

### Alternatives Considered
1. Install pip system-wide with `apt install python3-pip` — requires host modification; spec says not to change host software without approval.
2. Use `pipx` for tool installation — good for CLI tools but not for project dependencies.
3. Use `uv` (a fast pip replacement) — not installed; would require host change.
4. Use `pyproject.toml` + `hatch`/`poetry` — additional tooling not in the spec; overkill for MVP.

### Reason
`venv` is part of Python's standard library — no host changes needed. `--upgrade-deps` ensures pip inside the venv is up to date even if the system ensurepip seed is old.

### Trade-offs
Developers must activate the venv before working. CI and Dockerfiles must explicitly create/activate the venv. Slightly more setup steps in README.

### Consequences
- `backend/.venv/` and `agent/.venv/` are created locally (gitignored).
- Docker images will `RUN python3 -m venv /app/.venv && . /app/.venv/bin/activate && pip install -r requirements.txt`.
- CI workflows will cache the venv by hashing requirements.txt.

### Related Files
`backend/requirements.txt`, `agent/requirements.txt`, `docker-compose.yml`, `.github/workflows/`

---

## DEC-003 — Synchronous vs Asynchronous SQLAlchemy
**Date:** 2026-11-05  
**Status:** PROPOSED

### Context
FastAPI supports both synchronous and asynchronous Python. SQLAlchemy 2.x has both a sync and an async engine/session. We need to decide which to use for database access.

### Decision
**Use async SQLAlchemy** (`AsyncSession`, `create_async_engine`) with `asyncpg` as the PostgreSQL driver. This integrates naturally with FastAPI's async request handlers and avoids thread-pool overhead for I/O-bound database operations.

### Alternatives Considered
1. Sync SQLAlchemy with `psycopg2` — simpler to reason about, but blocks the event loop in FastAPI; acceptable for low concurrency but suboptimal.
2. Async SQLAlchemy with `aiosqlite` — SQLite only; not suitable for production.
3. Encode Databases library — adds another abstraction; SQLAlchemy is already in the spec.

### Reason
FastAPI is an ASGI framework designed for async code. Using async SQLAlchemy means database I/O does not block the event loop, which is important when handling WebSocket connections simultaneously with REST requests. `asyncpg` is the fastest async PostgreSQL driver for Python.

### Trade-offs
- Async SQLAlchemy has a steeper learning curve (session management, `async with`, `await`).
- Some ORM patterns (lazy loading) don't work in async mode — we use explicit `selectinload`/`joinedload` for relationships.
- Celery workers run in their own processes and are synchronous — they use a **separate sync engine** (psycopg2) for database writes. This means maintaining two engine configurations (async for FastAPI, sync for Celery). Clearly documented and tested.

### Consequences
- `asyncpg` added to backend requirements.
- Celery workers use `psycopg2` or `psycopg2-binary`.
- Database session dependency is `async def get_db() -> AsyncGenerator[AsyncSession, None]`.
- All repository functions are `async`.

### Related Files
`backend/app/database/`, `backend/app/core/config.py`, `backend/requirements.txt`

---

## DEC-004 — Agent Credential Scheme
**Date:** 2026-11-05  
**Status:** PROPOSED

### Context
Each agent must have a revocable, authenticated identity. We need to decide how agent credentials are issued, stored, and verified.

### Decision
On provisioning, generate a cryptographically random secret (32 bytes → 64-char hex or UUID4-style token). Return the plaintext secret **once** to the administrator. Store only the **bcrypt hash** of the secret in PostgreSQL. On every agent request, the agent sends `agent_id` + `agent_secret` in an HTTP header (`X-Agent-ID` and `X-Agent-Secret`, or HTTP Basic Auth). The backend hashes the incoming secret and compares it to the stored hash.

### Alternatives Considered
1. JWT tokens for agents — adds expiry complexity and requires refresh; revocation requires a blocklist; overkill for agents that have long-lived credentials.
2. mTLS — strong but adds certificate management overhead; out of scope for local MVP.
3. HMAC-signed requests — good but adds signing/verification logic; bcrypt is simpler.
4. Plain API key (no hash) — storing plaintext secrets in the database is a security failure.

### Reason
bcrypt provides work-factor-based hashing with built-in salt. Storing only the hash means a database breach does not expose working credentials. One-time reveal on provisioning is a common pattern (GitHub PATs, Stripe secret keys). The admin records the secret at provisioning time; it cannot be recovered later (only rotated).

### Trade-offs
- bcrypt is relatively slow (intentionally) — this is fine because agent authentication does not need to be blindingly fast and is not on the hot path.
- If an agent loses its secret, it must be rotated; there is no recovery.
- Two-header scheme (`X-Agent-ID` + `X-Agent-Secret`) is simple but means the secret travels in every request header; HTTPS is required for production use.

### Consequences
- `passlib[bcrypt]` added to backend requirements.
- Agents store their secret in an env variable or secure file, never in `config.yaml`.
- Rotation endpoint returns the new secret once and immediately invalidates the old hash.

### Related Files
`backend/app/api/v1/agents.py`, `backend/app/models/agent.py`, `backend/app/core/security.py`

---

## DEC-005 — Browser User Authentication (JWT vs Session Cookie)
**Date:** 2026-11-05  
**Status:** PROPOSED

### Context
Dashboard users (humans with browsers) need to authenticate. The spec warns against long-lived tokens in localStorage and requires careful consideration of expiry, refresh, storage, revocation, and CSRF.

### Decision
Use **short-lived JWTs in HttpOnly, Secure, SameSite=Strict cookies**. Access token: 15-minute expiry. Refresh token: 7-day expiry, also in an HttpOnly cookie. The `/auth/refresh` endpoint issues a new access token when the old one expires. Logout clears cookies and adds the refresh token's JTI to a Redis revocation set (expires with the token TTL).

### Alternatives Considered
1. JWT in localStorage — spec explicitly cautions against this; vulnerable to XSS.
2. Server-side sessions — requires session storage (can use Redis); simpler revocation but stateful server.
3. JWT in memory only — lost on page refresh; poor UX.
4. Database-backed sessions — more robust revocation but higher DB load per request.

### Reason
HttpOnly cookies prevent JavaScript access, mitigating XSS theft. SameSite=Strict provides CSRF protection without requiring extra CSRF tokens for same-origin requests. Short access token TTL limits exposure. Redis-backed refresh token revocation keeps the server mostly stateless while supporting logout.

### Trade-offs
- Requires CORS and cookie configuration to work correctly with the Vite dev server.
- Redis must be available for logout/revocation (acceptable — Redis is already required).
- Slightly more complex than a pure stateless JWT scheme.

### Consequences
- `python-jose[cryptography]` or `authlib` added to backend requirements.
- Cookie settings in FastAPI middleware must be tuned per environment (dev vs production).
- Frontend does not need to manage tokens explicitly — cookies are sent automatically.

### Related Files
`backend/app/api/v1/auth.py`, `backend/app/core/security.py`, `frontend/src/services/auth.ts`

---

## DEC-006 — Disk and Network Metric Storage Schema
**Date:** 2026-11-05  
**Status:** PROPOSED

### Context
Disk metrics are per-mount-point and network metrics are per-interface. We need to decide: normalized child tables or JSONB in the main metric record?

### Decision
Use **normalized child tables**: `metric_disks` (with FK to `metric_records`) and `metric_networks` (with FK to `metric_records`). The main `metric_records` table stores scalar CPU and memory values. Per-mount and per-interface data live in their own rows.

### Alternatives Considered
1. JSONB on `metric_records` for disk and network — simpler schema, but loses indexing on mount point and interface name, making alert evaluation (e.g., disk threshold per mount point) harder.
2. Normalized child tables (selected) — more rows but enables indexed queries by mount point/interface, which the alert engine needs.
3. Hybrid: JSONB for raw storage, materialized views for querying — overengineered for MVP.

### Reason
The alert engine needs to evaluate disk utilization per mount point and network errors per interface. If those values are buried in JSONB, every evaluation requires JSONB extraction, which is slower and less type-safe. Normalized tables allow `WHERE mount_point = '/data'` with an index.

### Trade-offs
- More tables and joins.
- Insert is slightly more complex (must insert child rows in the same transaction).
- Flexible number of disks/interfaces per sample is naturally handled by multiple child rows.

### Consequences
- Alert rules reference a `dimension` field (mount point or interface name).
- `metric_aggregates` table also has a `dimension` column to store per-mount/per-interface aggregates.

### Related Files
`backend/app/models/metric.py`, Alembic migrations

---

## DEC-007 — Celery Justification at MVP Scale
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
The spec requires Celery. Some engineers might argue it is overengineered for a single developer running locally. We need to document the justification.

### Decision
Use Celery with Redis broker as specified. The spec requires it, but it is also genuinely justified.

### Reason
1. **Decoupling**: The ingestion API does not block waiting for metric persistence or alert evaluation. This is correct architecture for reliability.
2. **Retry logic**: Celery provides configurable retry with backoff out of the box.
3. **Scheduled tasks**: Celery Beat handles retention cleanup and heartbeat monitoring.
4. **Observability**: Flower or the Celery CLI shows task queue depth, retries, and failures.
5. **Idempotency**: The `processed_batches` table + task `task_id` provides deduplication.

### Trade-offs
- Adds Redis dependency (already needed for other features).
- Worker restarts or failures mean tasks must be retried — handled via ACK-after-processing.
- Local developer must run Redis + Celery worker alongside the API (handled by Docker Compose).

### Consequences
Celery worker is a required service in `docker-compose.yml`. It shares the backend application code but runs as a separate process.

---

## DEC-008 — WebSocket Authentication
**Date:** 2026-11-05  
**Status:** PROPOSED

### Context
WebSocket connections cannot send standard HttpOnly cookies in the same way as HTTP requests in some browser/CORS configurations. We need to authenticate WebSocket upgrade requests.

### Decision
On WebSocket connection, the frontend sends the access token as a query parameter (`?token=<jwt>`) in the WebSocket URL. The backend validates the JWT on upgrade. This is a one-time validation at connect time. The token is short-lived (15 min); the frontend reconnects (WebSocket close → re-upgrade) using a new token.

### Alternatives Considered
1. HttpOnly cookie — browsers do send cookies on WebSocket upgrade if same origin; but cross-origin setup in dev requires care.
2. First message authentication — connect unauthenticated, send credentials as first message — more complex.
3. Query parameter JWT (selected) — simple, works across origins, standard for WebSocket auth.

### Reason
Query parameter is the simplest pattern that works reliably in browser–server WebSocket scenarios. The token is short-lived so the exposure window if logged is small. HTTPS in production encrypts the URL.

### Trade-offs
- Token appears in server access logs if not filtered — log filtering must be applied.
- Must reconnect when access token expires (every 15 min) — handled by frontend reconnect logic.

### Consequences
Frontend WebSocket hook must track token expiry and reconnect proactively.

---



---

## DEC-009 — Containerized Python 3.12 Development and Testing Strategy
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
The host machine runs Ubuntu 26.04 with Python 3.14.4. Key backend packages with compiled C extensions (`pydantic-core`, `asyncpg`, `psycopg2-binary`) do not yet provide pre-compiled wheels for Python 3.14 on Linux, and source builds require bleeding-edge rust/maturin ABI3 configurations that fail in standard pip environments.

### Options
1. Install Python 3.12 directly on the host using deadsnakes or building from source — modifies host system against spec guidelines.
2. Build and run all backend runtime, tests, linters, and type checkers inside a reproducible `python:3.12-slim` Docker container.

### Decision
Option 2: Build and run backend development tasks inside a multi-stage Docker container based on `python:3.12-slim`.

### Reason
- Respects the constraint not to modify host software or system packages without necessity.
- Matches the production deployment target where the backend runs in a Linux container.
- Guarantees 100% reproducible dependencies and wheel compatibility across any developer machine.
- Placing the container virtualenv in `/opt/venv` ensures that mounting the local project directory into `/app` does not shadow or collide with container binaries.

### Trade-offs
- Commands like `pytest` and `ruff` are invoked via Docker (`docker run --rm -v $(pwd)/backend:/app opspulse-backend:test ...`).
- Fast and reliable once the base image is built.

### Consequences
- CI and local dev commands will execute via Docker or Python 3.12.
- Host agent (when built on Day 4) uses pure Python standard libraries or wheels available for Python 3.14 (psutil has wheels).


---

## DEC-010 — Database Connection Pooling Strategy (AsyncAdaptedQueuePool vs NullPool)
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
In asynchronous Python applications using SQLAlchemy and `asyncpg`, connections stored in a connection pool are bound to the `asyncio` event loop that created them. In production under Uvicorn/FastAPI, a single long-lived event loop runs for the lifetime of the process. In automated test runners (`pytest-asyncio` with function-scoped loops), each test function runs in a distinct event loop. When a test finishes and closes its loop, any connection retained in the pool retains a pointer to the closed loop, triggering `RuntimeError: Task got Future attached to a different loop` on subsequent tests.

### Options Considered
1. Session-scoped event loop in pytest — forces all tests to share one event loop, which can hide concurrency bugs or state leakage between tests.
2. Explicit `NullPool` in testing and debug environments — each session creates and closes its own socket connection with no persistent pooling across distinct test loops.
3. Dispose engine before every test — requires teardown boilerplate in every test module.

### Decision
Option 2: Dynamically select `poolclass=NullPool` when `settings.DEBUG or settings.TESTING` is active, and use `AsyncAdaptedQueuePool` with `pool_pre_ping=True` in production. Additionally, provide a `db_session` fixture in `conftest.py` with `NullPool` for all integration tests.

### Reason
- Eliminates cross-loop connection contamination in pytest with zero boilerplate in test cases.
- Ensures production retains high-performance connection reuse via `AsyncAdaptedQueuePool`.
- `pool_pre_ping=True` ensures that any stale socket disconnected by PostgreSQL or network restarts is automatically discarded and renewed.

### Trade-offs
- Tests open and close connections per session, introducing a minor (~10ms) overhead per test, which is negligible for our test suite (8 tests execute in <1s).

### Consequences
- All integration tests run cleanly without event loop conflicts.
- Production handles high-concurrency requests with connection reuse.


---

## DEC-011 — Non-Blocking CPU Metric Collection Strategy
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
In Python, calling `psutil.cpu_percent(interval=1.0)` blocks the calling thread for 1.0 second while sleeping to measure time deltas. In a monitoring agent that collects multiple subsystems concurrently or operates on a strict collection loop (e.g. 10-second batch intervals), blocking the main loop introduces latency, drifts scheduling timers, and delays heartbeats.

### Options Considered
1. Blocking interval (`psutil.cpu_percent(interval=0.5)`) — blocks the runtime thread; unacceptable for responsive agent execution.
2. Background thread continuously polling CPU — introduces thread synchronization overhead, locks, and unnecessary CPU wakeups.
3. Non-blocking delta sampling (`interval=None`) — `psutil` compares system CPU counters against the values stored from the previous call.

### Decision
Option 3: Use `psutil.cpu_percent(interval=None)`. During `CpuCollector.__init__()`, prime the internal counters once. Each subsequent call to `.collect()` computes the exact utilization percentage accumulated since the prior sample with zero sleep or thread blocking.

### Reason
- Zero thread blocking allows the agent loop to execute in sub-millisecond time.
- Low overhead; avoids wasting CPU cycles sleeping or managing polling threads.
- Accurate: the delta reflects the actual interval between agent scheduler ticks.

### Trade-offs
- The very first call during `__init__` returns an arbitrary baseline (often 0.0), which is why we discard the first sample in `__init__` and only expose measurements from subsequent ticks.

### Consequences
- CPU metrics collection executes instantaneously (<1ms).
- Agent collection scheduler maintains jitter-free precision.


---

## DEC-012 — Safe Zero-Swap and Virtual Memory Collection Strategy
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
On modern Linux systems, swap configuration varies dramatically: physical developer workstations and laptops frequently configure swap partitions or swap files (e.g. 4–8 GB), whereas container runtimes (Docker, Kubernetes) and certain cloud VM configurations disable swap entirely (`swap.total == 0`). In unhandled implementations, calculating swap utilization can trigger `ZeroDivisionError` or produce `NaN`.

### Options Considered
1. Raise an error when swap is unavailable — breaks agent execution in containerized or headless environments.
2. Omit swap metrics when total == 0 — makes payload schemas irregular and unpredictable for backend workers.
3. Explicitly guard total swap: return `usage_percent = 0.0` when `total_bytes == 0` while still capturing accurate zero values.

### Decision
Option 3: Guard `total_bytes`. When `sm.total > 0`, use `float(sm.percent)`. When `sm.total == 0`, report `0` for total/used/free bytes and `0.0` for `usage_percent`. Wrap swap collection in a try/except block to gracefully degrade to `swap=None` if OS permission constraints forbid accessing `/proc/swaps`.

### Reason
- Ensures predictable Pydantic payloads across diverse environments (bare metal, laptops, VMs, Docker containers).
- Protects against division-by-zero crashes.
- Accurately conveys that zero swap is actively utilized when swap is disabled.

### Consequences
- Backend alert rules for swap will not trigger false positives on hosts without swap.
- Agent runs cleanly inside both containerized simulations and real host machines.


---

## DEC-013 — Direct Bcrypt Hashing over Deprecated Passlib
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Upstream `passlib` has been unmaintained for several years and fails on Python 3.12+ environments running modern `bcrypt >= 4.1.0`. Passlib inspects `bcrypt.__about__.__version__`, which was deprecated and removed in recent releases, causing Passlib to trigger erroneous 72-byte truncation test failures.

### Decision
Use standard, native `bcrypt` (`hashpw`/`checkpw`) directly in `app/core/security.py`. All inputs are explicitly encoded to UTF-8 and bounded to 72 bytes.

### Reason
- Eliminates dependency on unmaintained code.
- Eliminates Python deprecation warnings (`crypt` module removal).
- High performance, type-safe, and native C-extension speed.

---

## DEC-014 — HttpOnly Session Cookies with Bearer Fallback
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Browser clients storing authentication tokens in `localStorage` are vulnerable to token theft via Cross-Site Scripting (XSS). Headless API clients and CLI commands require bearer tokens in the `Authorization` header.

### Decision
Set `access_token` in an `HttpOnly`, `SameSite=Strict` cookie upon login (`/api/v1/auth/login`). Allow `app/api/deps.py:get_current_user` to check `request.cookies.get("access_token")` first, with fallback to `Authorization: Bearer <token>`.

### Reason
- Mitigates XSS attack vectors for web dashboard users.
- Retains compatibility for headless scripting, automated testing, and CLI integrations.

---

## DEC-015 — Guaranteed Audit Persistence on Failure
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Security events like failed logins, credential revocations, or unauthorized role attempts often culminate in an `HTTPException`. Standard database session wrappers abort and rollback on unhandled exceptions, inadvertently discarding the audit event.

### Decision
`record_audit_log` commits its database transaction immediately upon insertion.

### Reason
- Preserves immutable security logs even when request execution terminates in an HTTP error code.
- Satisfies spec Section 17.10 requirements.

---

## DEC-016 — Agent Identity Anti-Spoofing Check
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
An agent presenting valid `X-Agent-ID` and `X-Agent-Secret` headers could maliciously or accidentally transmit a payload claiming to originate from a different host UUID.

### Decision
`POST /api/v1/metrics/ingest` validates that `batch.agent_id == str(current_agent.id)`. Any divergence returns HTTP 400 Bad Request.

### Reason
- Prevents identity spoofing and cross-host data pollution.

---

## DEC-017 — Bounded Batch Size Enforcement
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Unbounded metric arrays can cause memory exhaustion on worker nodes.

### Decision
Enforce `min_length=1` and `max_length=100` on `MetricBatch.metrics` at the Pydantic schema validation layer.

### Reason
- Fast, declarative rejection (HTTP 422) before allocating database or Celery resources.

---

## DEC-018 — Kombu & Redis Version Pinning
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Celery 5.4.0's extra dependencies require `redis < 6.0.0`, while unpinned Kombu 5.7.0 requires `redis >= 6.1.0`.

### Decision
Pin `kombu==5.4.2` and `redis==5.2.0` in `backend/requirements.txt`.

### Reason
- Ensures complete compatibility across Celery, Kombu, and Redis.

---

## DEC-019 — 503 Service Unavailable on Queue Failure
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
If Redis or Celery is unavailable when an agent transmits a batch, returning 200 or 500 would lead to lost telemetry.

### Decision
Return HTTP 503 Service Unavailable when `process_metric_batch.delay()` fails.

### Reason
- Instructs the agent's retry client to retain unsent telemetry in its ring buffer.

---

## DEC-020 — Relational Normalization with ON DELETE CASCADE
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Monitored hosts have multiple disk partitions and network interfaces per sample.

### Decision
Store `metric_records` as the parent, with foreign-key cascaded child tables `metric_disks` and `metric_networks`.

### Reason
- Enables fast relational queries per partition and automatic cleanup when parent records expire.

---

## DEC-021 — Idempotent Metric Downsampling
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Downsampling tasks can overlap or be rerun.

### Decision
Define a unique constraint on `(agent_id, metric_key, dimension, bucket_start, bucket_size)` using PostgreSQL's `NULLS NOT DISTINCT` support.

### Reason
- Guarantees downsampling is strictly idempotent.

---

## DEC-022 — Role-Based Access for Alert Rule Management
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Alert rules govern incident generation and operational alerts.

### Decision
Viewers have read-only access (`GET /alerts/rules`). Only `ADMIN` and `OPERATOR` roles may create, update, or delete alert rules.

### Reason
- Enforces strict operational boundaries while maintaining observability.

---

## DEC-023 — Alert Rule Auditability
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Spec Section 17.10 requires logging alert-rule modifications.

### Decision
Every alert rule creation, modification, and deletion creates an entry in `audit_logs` capturing the actor user UUID and diff metadata.

### Reason
- Complete accountability for operational threshold changes.

---

## DEC-024 — Window-Based Sample Evaluation in Transactional Pipeline
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Metric evaluation must observe temporal trends across recent samples, not just a single instantaneous sample.

### Decision
The Alert Engine queries recent samples within `evaluation_window_seconds` from PostgreSQL with `selectinload` for child disk/network entities, ensuring full dimension fidelity without N+1 query overhead.

---

## DEC-025 — Compound Active Index for Incident Deduplication
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Checking whether an active incident exists for an agent and rule must be sub-millisecond fast.

### Decision
Created compound B-tree index `ix_incidents_active_lookup` on `(agent_id, rule_id, dimension, status)` to make deduplication lookups instant.

---

## DEC-026 — Automatic Clear Tracking with Dedicated Event Type
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Operators need to know whether an issue was manually resolved or self-healed by the infrastructure.

### Decision
Auto-recovered incidents record an explicit `AUTO_CLEARED` timeline event with system actor (`actor_user_id=None`) and measured normal value.

---

## DEC-027 — Event-Sourced Incident History
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Compliance and post-mortem analysis require an immutable log of who took what action on an incident and when.

### Decision
All state transitions, auto-clearances, and investigation notes are recorded as chronological `IncidentEvent` rows linked to the parent incident with cascading deletes.

---

## DEC-028 — State Machine Transition Enforcement
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Arbitrary state jumps (e.g. acknowledging after resolution) create corrupt incident histories.

### Decision
Endpoints explicitly validate the starting state before mutating, ensuring lifecycle integrity and proper attribution.

---

## DEC-029 — Asynchronous Heartbeat Monitor with Inbound Ping Auto-Clearance
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Detecting missing heartbeats requires a periodic background evaluation, whereas detecting recovery can happen immediately when an incoming HTTP ping arrives.

### Decision
Degradation and offline transitions are driven asynchronously by Celery task `monitor_agent_health`, while recovery happens synchronously inside `POST /api/v1/agents/heartbeat` for sub-second incident resolution.

---

## DEC-030 — Vite Bundler with Localhost Reverse Proxy
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
During local development, the frontend runs on port 5173 while FastAPI runs on port 8000. Cross-origin cookie exchange with `HttpOnly SameSite=Strict` cookies can fail if not on the same origin.

### Decision
Configured Vite dev server proxy to forward `/api` requests directly to `http://localhost:8000`, ensuring cookies and sessions work seamlessly in development without CORS complexity.

---

## DEC-031 — Client-Side Stat Aggregation from Normalized APIs
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Monolithic overview endpoints couple backend database queries to specific UI widget layouts.

### Decision
Frontend queries `/agents` and `/incidents` concurrently via `Promise.all` and aggregates fleet counts on the client, maintaining lean, decoupled REST APIs.

---

## DEC-032 — High-Density Area and Line Charts via Recharts
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Raw tabular metric data makes identifying CPU spikes or memory leaks slow and tedious.

### Decision
Integrated Recharts responsive vector charts (`AreaChart`, `LineChart`) styled with custom SVG gradients matching the dark dashboard theme.

---

## DEC-033 — Sticky Master-Detail Incident Triaging Layout
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Navigating away to separate pages for each incident slows down triage during multi-host outages.

### Decision
Implemented an inline master-detail slide-in panel that allows operators to inspect and resolve multiple alerts without losing their filter context or list scroll position.

---

## DEC-034 — Jittered Exponential Backoff for Real-time WebSockets
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Server restarts or network blips can cause hundreds of browser tabs to reconnect simultaneously, creating a thundering herd.

### Decision
Frontend hook uses randomized exponential backoff with a 15-second cap and graceful fallback to regular REST polling.

---

## DEC-035 — Two-Phase Approval and Dry-Run Guardrails for Remediation
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Triggering remediation actions during outages must avoid exacerbating service failures through unchecked automated commands.

### Decision
Implemented a two-phase approval workflow where Operators can request remediation, but actions flagged with `requires_approval` pause in `PENDING_APPROVAL` until explicitly authorized by an Administrator. All actions support safe `dry_run` verification.

---

## DEC-036 — Strictly Bounded and Self-Cleaning Failure Injections
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Host resource generators can easily run away, fill disk space, or trigger kernel Out-Of-Memory (OOM) panics.

### Decision
All simulation scripts enforce strict maximum memory/file caps and hard execution timeouts, with all allocations and files cleaned up inside guaranteed `try...finally` blocks.

---

## DEC-037 — Fail-Fast 503 Ingestion Semantics for Broker Outages
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
If the queue broker (Redis) is down, an ingestion endpoint might swallow errors or return 500 without informing the agent whether the data was saved.

### Decision
Ingestion routes catch queue transport exceptions and return HTTP 503 with a structured retry message. This triggers the agent's exponential backoff and ring buffer retention, guaranteeing zero metric loss during broker downtime.

---

## DEC-038 — Dual-Layer Frontend Verification with Vitest and Playwright
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Component unit tests verify UI logic in isolation with mocked APIs, but cannot catch browser-specific layout, routing, or bundling bugs.

### Decision
Standardize on Vitest with JSDOM for fast component assertions, complemented by headless Playwright browser tests driven by system Google Chrome for authentic routing and DOM verification.

---

## DEC-039 — Strict Warning Hygiene in Automated CI/Test Pipelines
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
Unfiltered third-party library warnings drown out actual application regressions and decrease developer confidence.

### Decision
Configure explicit warning filters in `pyproject.toml` scoped to external packages (`jose.*`, `httpx.*`), enforcing that internal code remains completely free of deprecation patterns.

---

## DEC-040 — Production Nginx Edge Routing with Native WebSocket Forwarding
**Date:** 2026-11-05  
**Status:** ACCEPTED

### Context
In local development, Vite handles reverse proxying. In production containerization, a dedicated, battle-tested edge web server is required.

### Decision
Deploy Nginx in the frontend container configured to proxy both standard REST HTTP calls and persistent full-duplex WebSocket connections (`/api/v1/ws`) to the backend with appropriate `Upgrade` and `Connection` headers.
