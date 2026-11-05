# OpsPulse — Architecture

> Update this file whenever the design or data flow changes.

---

## System Overview

OpsPulse is a local-first, distributed infrastructure monitoring and incident management platform. All components run on a single Ubuntu machine (or small LAN) using Docker Compose.

```
REAL UBUNTU HOST              SIMULATED HOSTS (Docker containers)
      |                                  |
      v                                  v
 Monitoring Agent                  Monitoring Agent(s)
 (Python, psutil)                 (same code, different configs)
      |                                  |
      +----------------+-----------------+
                       |
           HTTP POST /api/v1/metrics/ingest
           HTTP POST /api/v1/agents/heartbeat
                       |
                       v
           ┌─────────────────────┐
           │   FastAPI Backend   │  (port 8000)
           │  - Auth middleware  │
           │  - Input validation │
           │  - Publish to Redis │
           └─────────┬───────────┘
                     │
              Redis Broker  (port 6379)
                     │
                     v
           ┌─────────────────────┐
           │   Celery Worker(s)  │
           │  - Process batches  │
           │  - Persist metrics  │
           │  - Evaluate alerts  │
           │  - Manage incidents │
           └──────────┬──────────┘
                      │
         ┌────────────┴──────────────┐
         v                           v
  PostgreSQL DB               Event Publisher
  (port 5432)                 (FastAPI internal)
                                     │
                                     v
                           WebSocket Gateway
                           (FastAPI endpoint)
                                     │
                                     v
                           ┌──────────────────┐
                           │  React Dashboard │  (port 5173)
                           │  - Overview      │
                           │  - Infrastructure│
                           │  - Incidents     │
                           │  - Alert Rules   │
                           │  - Settings      │
                           └──────────────────┘
```

## Component Responsibilities

### Monitoring Agent (`agent/`)
- Collects CPU, memory, disk, network, and (optionally) process metrics using `psutil`
- Runs on each monitored host (real Ubuntu host or simulated Docker container)
- Authenticates to the backend using `agent_id` + `agent_secret` headers
- Sends metric batches at a configurable interval (default: 10 seconds)
- Sends heartbeats at a configurable interval (default: 30 seconds)
- Maintains a bounded local queue while the backend is unavailable
- Retries with exponential backoff and jitter
- Shuts down gracefully on SIGTERM/SIGINT

### FastAPI Backend (`backend/`)
- Validates all incoming requests (Pydantic schemas)
- Authenticates users (JWT in HttpOnly cookies) and agents (bcrypt-hashed secret)
- Publishes metric batches to Redis (does not process them synchronously)
- Returns success only after Redis publication is confirmed
- Provides REST APIs for all data access
- Provides authenticated WebSocket endpoint for dashboard updates
- Never performs heavy metric processing in the request handler

### Redis
- Message broker for Celery tasks
- Short-term storage for refresh token revocation JTIs
- Result backend for Celery (optional for MVP)

### Celery Worker
- Receives metric batch tasks from Redis
- Validates schema and agent association
- Checks idempotency via `processed_batches` table
- Persists metric records to PostgreSQL
- Evaluates applicable alert rules
- Creates or updates incidents
- Publishes dashboard events via FastAPI internal channels
- Runs scheduled tasks: heartbeat health check, metric retention cleanup, metric downsampling

### PostgreSQL
- Primary persistence layer
- Stores: users, agents, metric records, metric disk/network child rows, alert rules, incidents, incident events, metric aggregates, processed batches, recovery policies/executions, audit logs

### React Dashboard (`frontend/`)
- Displays real data from the backend REST APIs
- Receives real-time updates via authenticated WebSockets
- Falls back to REST polling on WebSocket disconnection
- Pages: Overview, Infrastructure, Machine Detail, Incidents, Alert Rules, Settings

## Data Flows

### Metric Ingestion Flow
```
Agent → POST /api/v1/metrics/ingest (auth headers + JSON payload)
  → FastAPI validates payload and agent credentials
  → FastAPI publishes Celery task to Redis
  → FastAPI returns HTTP 202 Accepted
Agent receives 202 (or retries on 5xx)

Redis → Celery worker picks up task
  → Worker checks idempotency (processed_batches table)
  → Worker persists metric_records + child disk/network rows
  → Worker evaluates alert rules
  → Worker creates/updates incidents
  → Worker publishes WebSocket events
```

### Heartbeat Flow
```
Agent → POST /api/v1/agents/heartbeat (auth headers)
  → FastAPI updates agent.last_heartbeat in DB
  → Returns 204 No Content

Celery Beat (scheduled every 30s) → check_agent_health task
  → For each agent, compare last_heartbeat to now
  → If age > 60s: mark DEGRADED, create/update offline incident
  → If age > 120s: mark OFFLINE, escalate incident
  → If heartbeat resumed: mark ONLINE, resolve offline incident
```

### Alert Evaluation Flow
```
Celery worker (after metric persistence)
  → Load enabled alert rules applicable to this agent
  → For each rule:
    - Query recent metric samples within evaluation window
    - Check consecutive breach count
    - If breach count >= required: check cooldown
    - If not in cooldown: check for existing open incident (deduplicate)
    - If no open incident: create new incident + incident event
    - If condition clears: resolve incident + create "cleared" event
```

### WebSocket Update Flow
```
Celery worker creates/updates incident
  → Publishes event to in-process event bus (or Redis Pub/Sub)
  → WebSocket gateway sends event to all subscribed authenticated clients
  → Dashboard updates incident list / status badges without full page reload
```

## Trust Boundaries

| Boundary | Authentication | Notes |
|---|---|---|
| Agent → Backend | X-Agent-ID + X-Agent-Secret (bcrypt) | Secret never stored in plaintext |
| Browser → Backend | JWT in HttpOnly cookie | 15-min access token, 7-day refresh |
| Celery → DB | Direct connection (trusted internal network) | Docker network only |
| Backend → Redis | No auth (Docker internal network) | Add Redis AUTH for production |
| Backend WS → Client | JWT in ?token= query param | Validated on upgrade |

## Database Schema Summary

| Table | Purpose |
|---|---|
| `users` | Dashboard user accounts |
| `agents` | Monitored host identities + credential hashes |
| `metric_records` | Per-sample CPU + memory scalars |
| `metric_disks` | Per-mount-point disk metrics (FK to metric_records) |
| `metric_networks` | Per-interface network metrics (FK to metric_records) |
| `alert_rules` | Configurable threshold rules |
| `incidents` | Active and historical incidents |
| `incident_events` | Chronological incident state transitions |
| `metric_aggregates` | Downsampled metrics for long-range dashboard queries |
| `processed_batches` | Idempotency tracking for Celery tasks |
| `recovery_policies` | Allowlisted automated actions (advanced feature) |
| `recovery_executions` | Execution history for recovery actions |
| `audit_logs` | Security and admin audit trail |

## Port Map

| Service | Port | Notes |
|---|---|---|
| FastAPI | 8000 | REST API + WebSockets |
| React (Vite dev) | 5173 | Frontend dev server |
| PostgreSQL | 5432 | Not exposed publicly in production |
| Redis | 6379 | Not exposed publicly in production |

## Technology Decisions Summary

| Decision | Choice | Rationale |
|---|---|---|
| DB access style | Async SQLAlchemy + asyncpg | Native async for FastAPI; Celery uses sync psycopg2 |
| Agent auth | bcrypt-hashed secret | One-time reveal; no plaintext in DB |
| User auth | JWT in HttpOnly cookie | XSS-resistant; CSRF-safe with SameSite=Strict |
| WebSocket auth | JWT in query param | Standard, works across origins |
| Disk/network storage | Normalized child tables | Enables indexed queries per mount/interface |
| Message broker | Redis | Already required; Celery native support |
| Idempotency | processed_batches table | Deduplicates both API resends and Celery retries |

---

*Last updated: 2026-11-05 — Day 1 (planning and scaffolding)*
