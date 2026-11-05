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
