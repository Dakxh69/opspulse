# OpsPulse — AI-Ready Project Specification

**Version:** 1.0  
**Project:** Distributed Infrastructure Monitoring & Incident Management Platform  
**Development approach:** AI-assisted, incremental, test-driven development  
**Primary environment:** Ubuntu Linux 24.04  
**Deployment target:** Local-first Docker Compose  
**Planned roadmap:** 30 development days (estimates, not artificial deadlines)

---

# 0. How to use this file

This file is both the technical specification and the instruction manual for the AI coding agent that will build OpsPulse.

1. Create a folder named `opspulse` on your machine.
2. Put this file in the root of that folder and keep its name as `spec.md`.
3. Open the **entire `opspulse` folder** in your AI coding tool (for example, Cursor, Claude Code, Codex, or another repository-aware coding agent).
4. Copy the **Initial Prompt** from Section 1 and send it to the AI.
5. The AI must read this complete specification, inspect the repository and environment, and prepare Day 1. It must not generate the entire project in one pass.
6. Work one development day at a time. At the end of every day, the AI must update the progress files and give you a report.
7. When you start a new AI conversation or switch tools, use the **Resume Prompt** from Section 2.

**Important:** A task being planned or having code generated does not mean it is complete. The AI must run checks and verify behavior before marking a task as complete. The AI must never invent test results, files, benchmark numbers, or successful deployments.

---

# 1. Initial Prompt — give this to the AI first

Copy everything inside this prompt block and send it to your AI coding agent after opening the `opspulse` folder:

> You are the lead software architect, senior backend engineer, DevOps engineer, and technical project manager responsible for building OpsPulse.
>
> Read the **entire `spec.md`** before taking action. Treat it as the authoritative project specification.
>
> **Do not build the whole project at once. Do not start writing application code immediately.**
>
> First complete a discovery and planning phase:
>
> 1. Inspect the current working directory, repository, existing files, Git status, and available development tools.
> 2. Inspect the installed versions of Ubuntu/Linux, Python, Node.js, npm, Docker, and Docker Compose. Do not install, remove, or upgrade host software without explaining why and getting my approval.
> 3. Read and understand the architecture, functional requirements, database design, APIs, security requirements, testing strategy, roadmap, and documentation rules in `spec.md`.
> 4. Identify ambiguities, dependencies, risks, potentially unnecessary complexity, and any requirements that need a technical decision.
> 5. Propose the implementation architecture for my local Ubuntu laptop. Explain the important technology choices and trade-offs, including database access style, agent identity and credential provisioning, Redis/Celery reliability, idempotency, metric retention, and WebSocket delivery.
> 6. Create the required documentation files listed in Section 4: `PROJECT_STATUS.md`, `DAILY_PROGRESS.md`, `DECISION_LOG.md`, `IMPLEMENTATION_LOG.md`, `TEST_REPORT.md`, `KNOWN_ISSUES.md`, `ARCHITECTURE.md`, and `DEVELOPMENT_HANDOFF.md`.
> 7. Prepare a detailed **Day 1 plan**. Include the objective, exact tasks, expected files, commands to run, risks, verification steps, and acceptance criteria.
> 8. Present your findings and Day 1 plan to me. Explain any important technical decisions and alternatives.
>
> **Stop after presenting the plan. Wait for my approval before implementing Day 1.**
>
> After I approve, implement Day 1 only. Do not silently start Day 2.
>
> At the end of every development day:
>
> - Run relevant tests, linters, type checks, or manual verification steps.
> - Report the exact commands executed and their real results.
> - Clearly distinguish `PLANNED`, `IMPLEMENTED`, `TESTED`, and `COMPLETE` work.
> - Update `docs/PROJECT_STATUS.md`.
> - Append a new dated entry to `docs/DAILY_PROGRESS.md`. Never overwrite earlier daily entries.
> - Update `docs/DECISION_LOG.md` for significant technical decisions, recording context, alternatives, reasons, trade-offs, and consequences.
> - Update `docs/IMPLEMENTATION_LOG.md` with modules and files implemented.
> - Update `docs/TEST_REPORT.md` with actual test commands and results.
> - Update `docs/KNOWN_ISSUES.md` when an issue remains or is discovered.
> - Update `docs/DEVELOPMENT_HANDOFF.md` so a new AI session can continue without losing context.
> - Update `docs/ARCHITECTURE.md` if the architecture or data flow changes.
> - Give me the daily report using the exact template in Section 5.
> - Stop and wait for my next instruction before starting the next development day.
>
> Explain important coding decisions while working, not only at the end. For each significant decision, tell me what problem is being solved, what options were considered, why one was selected, and what trade-offs it introduces. Do not waste time explaining trivial imports or every line of code.
>
> Never fake test results, claim unverified features are complete, hide failures, or overwrite working code without inspecting it. Never run destructive commands or change host-level configuration without approval. Use safe, bounded test simulations. If a requirement is unsafe or technically unsound, explain why and propose a safer alternative.
>
> The goal is a reproducible working application that can be cloned, started locally, connected to a real Ubuntu host agent, and tested using controlled simulated machines and failure scenarios.

---

# 2. Resume Prompt — use at the start of every new AI session

Use this prompt whenever you continue after a break or switch AI tools:

> Continue the existing OpsPulse project. Do not restart, scaffold over, or regenerate the project.
>
> First read these files:
>
> 1. `spec.md`
> 2. `docs/PROJECT_STATUS.md`
> 3. `docs/DEVELOPMENT_HANDOFF.md`
> 4. The latest entry in `docs/DAILY_PROGRESS.md`
> 5. `docs/DECISION_LOG.md`
> 6. `docs/KNOWN_ISSUES.md`
> 7. `docs/TEST_REPORT.md`
>
> Then inspect the actual repository, Git status, relevant source files, configuration, and current test state. Treat documentation as a guide, not proof. Verify it against the code and test results.
>
> Summarize what is genuinely complete, what is incomplete, the latest test status, open issues, any discrepancy between documentation and repository state, and the exact next task.
>
> Explain the plan and any important technical decisions before changing code. Do not modify code until you have presented this recovery summary and next-day plan and I have approved it. Once approved, continue with the next incomplete roadmap day only.
>
> Preserve existing decisions and history. If a decision changes, add a new entry to `DECISION_LOG.md` that references the earlier decision. Do not silently rewrite history. At the end of the session, follow the daily reporting and documentation requirements in `spec.md`.

---

# 3. Project overview

## 3.1 Problem statement

Applications run across physical machines, virtual machines, and containers. CPU saturation, memory pressure, disk exhaustion, network problems, and service failures can degrade performance or cause downtime. Without centralized monitoring, engineers must inspect machines manually and may discover failures late.

OpsPulse is a centralized, local-first infrastructure monitoring and incident management platform. It collects system metrics from monitored machines, transports them to a backend, processes them asynchronously, evaluates configurable alert rules, manages incidents, and displays infrastructure health in a web dashboard.

## 3.2 Main objective

Build a platform that can:

- Monitor the user's Ubuntu laptop as a real host.
- Monitor additional simulated Linux machines/containers.
- Collect CPU, memory, disk, network, and selected process metrics.
- Send metrics securely to a central backend.
- Process metric batches asynchronously.
- Store and query historical metrics.
- Detect threshold breaches and missed heartbeats.
- Create, acknowledge, investigate, resolve, and reopen incidents.
- Show current and historical metrics in a web dashboard.
- Support safe, explicitly allowlisted recovery actions as an advanced feature.
- Run locally without requiring paid cloud infrastructure.

## 3.3 Intended users

- System administrators.
- DevOps and platform engineers.
- Developers operating services.
- Small teams that need a self-hosted monitoring prototype.

## 3.4 MVP non-goals

Do not add these before the core monitoring pipeline works:

- Kubernetes operator or full Kubernetes monitoring.
- Windows/macOS monitoring agents.
- Enterprise SIEM functionality.
- Arbitrary remote shell execution.
- Machine-learning anomaly detection.
- Multi-region high availability.
- Mandatory paid cloud deployment.

---

# 4. Mandatory project memory and progress documentation

The AI must create and maintain these files inside the repository. These documents are part of the project deliverable, not optional notes.

```text
opspulse/
├── spec.md
├── docs/
│   ├── PROJECT_STATUS.md
│   ├── DAILY_PROGRESS.md
│   ├── DECISION_LOG.md
│   ├── IMPLEMENTATION_LOG.md
│   ├── TEST_REPORT.md
│   ├── KNOWN_ISSUES.md
│   ├── ARCHITECTURE.md
│   └── DEVELOPMENT_HANDOFF.md
```

## 4.1 `PROJECT_STATUS.md` — current project state

Update this file at the end of every development day. It must contain:

- Current roadmap day and phase.
- Overall status: `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, or `MVP COMPLETE`.
- Completion percentage based on verified acceptance criteria, not guesswork.
- Completed modules.
- In-progress modules.
- Pending modules.
- Latest unit, integration, and end-to-end test status.
- Known blockers.
- Exact next task.

Use these task statuses consistently:

- `NOT STARTED`
- `IN PROGRESS`
- `BLOCKED`
- `IMPLEMENTED`
- `TESTED`
- `COMPLETE`

A task may be marked `COMPLETE` only after implementation, relevant verification, and documentation are finished. `IMPLEMENTED` and `COMPLETE` are not interchangeable.

## 4.2 `DAILY_PROGRESS.md` — append-only daily journal

At the end of every development day, append a new dated section. Never delete or overwrite earlier daily entries.

Each entry must include:

1. Day number and date.
2. Planned objectives.
3. Tasks completed and incomplete, with checkboxes.
4. Files created, modified, or deleted.
5. Implementation summary.
6. Important decisions and their decision IDs.
7. Exact commands/tests executed and actual results.
8. Bugs encountered and how they were resolved.
9. Remaining issues and blockers.
10. Actual day status: `COMPLETE`, `PARTIALLY COMPLETE`, or `BLOCKED`.
11. Next day's exact plan.

Example format:

```markdown
## Day 1 — Repository and Environment Setup
Date: YYYY-MM-DD
Status: COMPLETE / PARTIALLY COMPLETE / BLOCKED

### Objectives
- [x] Inspect environment
- [x] Initialize repository
- [ ] Configure backend test tooling

### Files changed
- .gitignore
- README.md
- docs/PROJECT_STATUS.md

### Implementation summary
Explain what was actually implemented and why.

### Commands and verification
- `python --version` — record the actual output
- `git status --short` — record the actual result
- `pytest` — record the actual result; zero tests collected is not a passing test suite

### Decisions
- DEC-001 — Repository and environment strategy

### Issues
- None / list issue IDs

### Next day
- Configure the FastAPI application skeleton
```

The example is a format illustration only. It is not evidence that any task has already been performed.

## 4.3 `DECISION_LOG.md` — why the AI made technical choices

Record meaningful engineering decisions. Do not log trivial syntax choices or every import.

Every entry must contain:

- Sequential ID: `DEC-001`, `DEC-002`, etc.
- Date.
- Status: `PROPOSED`, `ACCEPTED`, `REJECTED`, or `SUPERSEDED`.
- Context/problem.
- Decision selected.
- Alternatives considered.
- Why the selected option was preferred.
- Trade-offs, risks, and limitations.
- Consequences for future modules.
- Related files or modules.

Example:

```markdown
## DEC-001 — Asynchronous metric processing
Status: PROPOSED
Date: YYYY-MM-DD

### Context
Metric ingestion should not wait for database persistence and alert evaluation.

### Options
1. Process all work inside the FastAPI request.
2. Publish a task to Redis and process it in a worker.

### Decision
Option 2: Redis + Celery.

### Reason
Separates ingestion from processing and allows worker scaling.

### Trade-offs
Adds Redis, Celery, retry handling, idempotency requirements, and operational complexity.

### Consequences
The API may report acceptance only after queue publication succeeds. Workers must safely handle retries and duplicate task delivery.
```

If a decision changes, add a new decision referencing the old ID. Preserve the historical entry. The AI must explain significant decisions to the user at the time they are made, not merely hide the explanation in this file.

Significant decision areas include architecture, database schema/indexing, authentication, queue reliability, idempotency, retries, caching, WebSockets, metric retention, Docker networking, performance, and security.

## 4.4 `IMPLEMENTATION_LOG.md`

For each implemented module, record:

- Module name and purpose.
- Implementation date.
- Files involved.
- Important public functions/classes.
- Dependencies and interfaces.
- APIs or data contracts.
- Tests and verification performed.
- Known limitations.

## 4.5 `TEST_REPORT.md`

Maintain cumulative test history:

- Date and test run identifier.
- Exact command executed.
- Environment details where relevant.
- Number passed, failed, skipped, and not collected.
- Failure details.
- Fix applied, if any.
- Current test status.

Never call “no tests collected” a passing test suite. Never claim a command was run if it was not run.

## 4.6 `KNOWN_ISSUES.md`

For every unresolved issue, record:

- Issue ID.
- Summary.
- Severity: `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`.
- Reproduction steps.
- Expected versus actual behavior.
- Related module.
- Workaround, if any.
- Current status and next action.

## 4.7 `ARCHITECTURE.md`

Maintain the current architecture, component responsibilities, data flows, trust boundaries, and diagrams. Update this file whenever a design or flow changes.

## 4.8 `DEVELOPMENT_HANDOFF.md`

Update this file at the end of every development session so another AI can continue accurately. Include:

- Current day and phase.
- Repository path and branch, if known.
- Last known commit, if known.
- Current Git working-tree status.
- Verified completed work.
- Incomplete work.
- Latest test state.
- Active issues.
- Recent decision IDs.
- Important files to inspect.
- Exact next task and its acceptance criteria.

Never store passwords, API keys, access tokens, private keys, or other secrets in documentation.

---

# 5. Mandatory end-of-day report to the user

At the end of every development day, the AI must print a report using this format:

```text
================================================
OPSPULSE — DAY X REPORT
================================================

OBJECTIVE
Today's planned outcome.

COMPLETED
[x] Verified task
[x] Verified task
[ ] Incomplete task

FILES CREATED / MODIFIED
- path/to/file
- path/to/another_file

IMPLEMENTATION SUMMARY
What was built and how it works.

IMPORTANT TECHNICAL DECISIONS
- DEC-00X: Decision
  Why: ...
  Alternatives: ...
  Trade-offs: ...

TESTS
- Command: ...
- Result: ...
- Passed / Failed / Skipped / Not collected: ...

ISSUES
- Resolved: ...
- Still open: ...

DOCUMENTATION UPDATED
- PROJECT_STATUS.md
- DAILY_PROGRESS.md
- DECISION_LOG.md (if a decision was made)
- IMPLEMENTATION_LOG.md
- TEST_REPORT.md
- KNOWN_ISSUES.md (if applicable)
- DEVELOPMENT_HANDOFF.md
- ARCHITECTURE.md (if changed)

DAY STATUS
COMPLETE / PARTIALLY COMPLETE / BLOCKED

NEXT DAY
Exact next objective.
================================================
```

The report must match the repository and documentation. Do not report success before verification. If only some tasks are complete, say so plainly and carry the unfinished work forward.

---

# 6. Technology stack and engineering constraints

| Layer | Technology | Purpose |
|---|---|---|
| Host agent | Python 3.12+ | Collect host metrics |
| Metrics library | psutil | CPU, memory, disk, network, processes |
| Backend | FastAPI | REST APIs and WebSockets |
| Validation | Pydantic | Input/configuration validation |
| ORM | SQLAlchemy 2.x | Database access |
| Migrations | Alembic | Schema versioning |
| Database | PostgreSQL | Persistent storage |
| Queue/broker | Redis | Asynchronous task transport |
| Worker | Celery | Metric processing and scheduled jobs |
| Frontend | React + TypeScript | Monitoring dashboard |
| Build tool | Vite | Frontend development |
| Styling | Tailwind CSS | UI styling |
| Charts | Recharts | Metric visualization |
| State | Redux Toolkit or simpler local state where justified | UI state |
| Realtime | FastAPI WebSockets | Dashboard events |
| Packaging | Docker | Service packaging |
| Orchestration | Docker Compose | Local deployment |
| Testing | Pytest | Agent and backend tests |
| Frontend testing | Vitest, React Testing Library, Playwright | Component and end-to-end tests |
| Linting | Ruff and ESLint | Code quality |
| Type checking | mypy or Pyright; TypeScript compiler | Static type safety |
| CI | GitHub Actions | Automated lint, type, and test checks |

The AI must explain and document important choices, including:

- Synchronous versus asynchronous SQLAlchemy.
- Whether Celery is justified at the current scale.
- How duplicate task delivery and idempotency are handled.
- How agent secrets are provisioned, hashed, rotated, and revoked.
- How browser sessions and API authentication work.
- How WebSocket users authenticate and reconnect.
- How metric retention and aggregation are implemented.

Do not add Kafka, Kubernetes, microservices, ML, or extra infrastructure merely to make the project sound advanced. Prefer the simplest architecture that meets the requirements.

---

# 7. High-level architecture

```text
REAL UBUNTU HOST              SIMULATED HOSTS / CONTAINERS
      |                                  |
      v                                  v
 Monitoring Agent                  Monitoring Agent(s)
      |                                  |
      +----------------+-----------------+
                       |
                 HTTP(S) / API
                       |
                       v
               FASTAPI INGESTION
                       |
                  REDIS BROKER
                       |
                       v
                 CELERY WORKER
                       |
               +-------+--------+
               |                |
               v                v
          POSTGRESQL        ALERT ENGINE
                                |
                                v
                         INCIDENT MANAGER
                                |
                         EVENT PUBLISHER
                                |
                                v
                         WEBSOCKET GATEWAY
                                |
                                v
                         REACT DASHBOARD
```

## 7.1 Monitoring agent

Runs on each monitored Linux host. It must:

- Collect metrics at a configurable interval.
- Attach agent identity and UTC timestamps.
- Send metric batches.
- Send heartbeats.
- Retry transient failures with exponential backoff and jitter.
- Maintain a bounded local queue while the backend is unavailable.
- Avoid excessive CPU, memory, disk, or network overhead.
- Log failures without exposing credentials.
- Shut down gracefully.

## 7.2 FastAPI backend

Responsibilities:

- User authentication and authorization.
- Agent provisioning and authentication.
- Metric ingestion and payload validation.
- Queue publication.
- Agent heartbeat handling.
- Alert-rule management.
- Incident APIs.
- Metrics query APIs.
- WebSocket event delivery.

The request handler must not perform heavy metric processing or long-running analysis synchronously.

## 7.3 Redis and Celery

Redis transports background tasks. Celery workers process batches, persist records, evaluate rules, and perform scheduled health checks.

Reliability rules:

- Queue acceptance must be confirmed before returning a successful ingestion response.
- Retries must be bounded and observable.
- Tasks must be idempotent where possible.
- Duplicate delivery must not create duplicate incidents.
- Failed tasks must be diagnosable.
- Define behavior when Redis or PostgreSQL is unavailable.

Design for at-least-once delivery with idempotent processing. Do not claim exactly-once processing.

## 7.4 PostgreSQL

Stores users, agents, metrics, alert rules, incidents, incident events, recovery policies, and recovery execution history.

## 7.5 Frontend

Displays real backend data, not permanent mock data. WebSocket updates must update relevant UI state without a full page reload. PostgreSQL remains the source of truth; WebSocket messages are notifications, not durable storage.

---

# 8. Monitoring agent requirements

## 8.1 CPU metrics

Collect:

- Overall CPU utilization percentage.
- Per-core utilization where practical.
- Logical CPU count.
- CPU frequency where supported.
- Load average where supported by the operating system.

## 8.2 Memory metrics

Collect:

- Total RAM.
- Used RAM.
- Available RAM.
- Memory utilization percentage.
- Swap total, used, and utilization.

## 8.3 Disk metrics

For each relevant mounted filesystem, collect:

- Mount point.
- Device/filesystem label where available.
- Total bytes.
- Used bytes.
- Available bytes.
- Utilization percentage.

Exclude pseudo-filesystems and duplicate mounts where appropriate. Document exclusions.

## 8.4 Network metrics

For each selected network interface, collect:

- Bytes sent and received counters.
- Packets sent and received counters.
- Errors and dropped packets.

Calculate traffic rates from counter deltas divided by elapsed time. Handle counter resets, interface disappearance, and the first sample.

## 8.5 Process metrics

Optional and configurable:

- PID.
- Process name.
- CPU percentage.
- Memory percentage.
- Process status.

Do not collect process command-line arguments or environment variables by default because they may contain secrets.

## 8.6 Example agent configuration

```yaml
agent:
  name: ubuntu-primary
  collection_interval_seconds: 10
  batch_size: 10
  local_buffer_max_batches: 100

backend:
  base_url: http://localhost:8000
  heartbeat_interval_seconds: 30

features:
  cpu: true
  memory: true
  disk: true
  network: true
  processes: false

recovery:
  enabled: false
  allowed_actions: []  # action IDs mapped to local commands; empty by default

logging:
  level: INFO
```

Credentials must be provided securely outside the committed configuration file.

## 8.7 Agent lifecycle

1. Load and validate configuration.
2. Authenticate or register using the approved provisioning flow.
3. Collect metrics.
4. Normalize and validate the payload.
5. Place data in the bounded local queue.
6. Send batches to the backend.
7. Retry transient failures with exponential backoff and jitter.
8. Send heartbeats.
9. Handle shutdown gracefully.

---

# 9. Agent identity and authentication

Each agent must have a unique identity and revocable credential.

Requirements:

- Secure credential generation.
- Store only a hash of long-lived agent secrets in PostgreSQL.
- Authenticate every agent request.
- Support credential rotation and revocation.
- Avoid logging secrets.
- Restrict agent endpoints to agent credentials.
- Never trust a client-supplied agent ID without verifying credential ownership.

The initial implementation may use a one-time provisioning flow that creates an agent and returns its secret only once. Document how an administrator provisions a new agent.

For browser users, use secure session handling. If JWTs are selected, document expiry, refresh, storage, revocation, and CSRF considerations. Do not store long-lived authentication tokens in browser localStorage by default.

---

# 10. Metric ingestion contract

Illustrative payload; the final validated Pydantic schema may evolve:

```json
{
  "agent_id": "agent-uuid",
  "batch_id": "unique-batch-id",
  "metrics": [
    {
      "timestamp": "2026-11-04T12:00:00Z",
      "cpu": {
        "usage_percent": 78.5,
        "logical_cores": 8
      },
      "memory": {
        "total_bytes": 16000000000,
        "used_bytes": 11000000000,
        "available_bytes": 5000000000,
        "usage_percent": 68.75
      },
      "disks": [],
      "networks": []
    }
  ]
}
```

Requirements:

- Validate identity and credential.
- Validate timestamps and numeric ranges.
- Reject malformed payloads with useful errors.
- Enforce request and batch size limits.
- Support idempotency with batch IDs or stable metric identifiers.
- Queue accepted batches.
- Return success only after queue publication succeeds.
- Never expose secrets or internal stack traces in API responses.

---

# 11. Metric processing and storage

Worker pipeline:

1. Receive queued batch.
2. Validate schema and agent association.
3. Check idempotency.
4. Normalize metric records.
5. Persist records transactionally.
6. Evaluate applicable alert rules.
7. Create or update incidents.
8. Publish dashboard events.
9. Record processing failures.

Use database indexes for agent and time-based queries. Consider time partitioning only if measured volume justifies it.

## 11.1 Metric retention

Initial configurable local policy:

- Raw metrics: 7 days.
- Aggregated metrics: 30 days.
- Incidents and audit events: retain according to an explicit policy.

A scheduled cleanup task must delete only eligible metric records. Never accidentally cascade-delete incident or audit history. Dashboard queries must use bounded time ranges, pagination, and aggregation/downsampling for longer time windows.

---

# 12. Alert engine

## 12.1 Default thresholds

| Metric | Warning | Critical |
|---|---:|---:|
| CPU utilization | 75% | 90% |
| Memory utilization | 80% | 95% |
| Disk utilization | 80% | 90% |
| Agent heartbeat age | 60 seconds | 120 seconds |

These are configurable starter defaults, not universal infrastructure standards.

## 12.2 Alert-rule fields

- ID and name.
- Metric key.
- Operator: `>`, `>=`, `<`, `<=`, `==`.
- Threshold.
- Severity.
- Evaluation window.
- Required consecutive breaches.
- Cooldown.
- Enabled flag.
- Optional agent scope.
- Optional dimension filter (mount point for disk, interface for network) and, when no filter is given for a per-dimension metric, the aggregation mode (evaluate each dimension separately, or use the maximum).

## 12.3 Evaluation behavior

- Evaluate only valid, recent samples.
- Support evaluation windows and consecutive breaches.
- Avoid alerting on a single transient spike when sustained breach is required.
- Deduplicate active incidents for the same agent, rule, and dimension (for example, mount point).
- Apply cooldown and recovery/clear behavior.
- Record when a condition starts and clears.
- Handle missing data separately from a zero-valued metric.

---

# 13. Incident management

## 13.1 Lifecycle

`OPEN → ACKNOWLEDGED → INVESTIGATING → RESOLVED → CLOSED`

Support reopening when the underlying condition returns.

## 13.2 Incident fields

- UUID.
- Agent reference.
- Alert-rule reference.
- Dimension (for example mount point or interface), when applicable.
- Title and description.
- Severity.
- Status.
- First detected time.
- Last seen/updated time.
- Acknowledging/resolving user.
- Resolution time and notes.

## 13.3 Features

- List/filter by status, severity, agent, and time.
- View incident details.
- Acknowledge incident.
- Add investigation notes.
- Resolve incident.
- Reopen incident.
- View chronological event history.

Every status transition must create an incident event with actor and timestamp.

---

# 14. Agent heartbeat and availability

Default heartbeat interval: 30 seconds.

Initial state rules:

- `ONLINE`: recent valid heartbeat.
- `DEGRADED`: heartbeat age exceeds 60 seconds.
- `OFFLINE`: heartbeat age exceeds 120 seconds.

Thresholds must be configurable. Use a scheduled worker or another reliable mechanism. Avoid creating a new incident on every scheduler tick. Deduplicate the offline incident and resolve/reopen it appropriately when the agent returns.

---

# 15. Dashboard requirements

## Page 1 — Overview

Display:

- Total agents.
- Online, degraded, and offline agents.
- Active incidents.
- Critical incidents.
- CPU and memory overview.
- Recent incident activity.

## Page 2 — Infrastructure

For each machine show:

- Name and hostname.
- OS and agent version.
- Agent status and last heartbeat.
- CPU, memory, and disk utilization.

## Page 3 — Machine details

Show:

- CPU history.
- Memory history.
- Disk history.
- Network throughput.
- Optional process summary.
- Time-range selection.
- Last heartbeat and agent metadata.

## Page 4 — Incidents

Show incident list, severity/status filters, details, timeline, notes, and acknowledge/resolve actions.

## Page 5 — Alert rules

Allow creating, updating, enabling/disabling, and configuring thresholds, evaluation windows, and cooldowns. Show clear validation errors.

## Page 6 — Settings and administration

Provide user/role management appropriate to the MVP, agent provisioning/revocation, audit visibility, and recovery policies when that feature is implemented.

## Realtime behavior

Use authenticated WebSockets for incident events and relevant metric/summary updates. Implement reconnect/backoff and a REST refresh fallback. WebSocket events are notifications, not durable storage.

---

# 16. Controlled recovery automation

This is an advanced feature. Do not implement it before monitoring, alerting, and incident handling are reliable.

Possible allowlisted actions:

- Restart a specifically configured systemd service.
- Restart a specifically configured Docker container.
- Run a predefined cleanup script.
- Run a predefined diagnostic.

Security requirements:

- Never accept arbitrary shell commands from API input.
- Use action identifiers mapped to preconfigured commands.
- Restrict executable paths and targets.
- Use least privilege; do not run the whole backend as root.
- Require explicit administrator configuration.
- Support manual approval for risky actions.
- Apply timeouts and concurrency controls.
- Sanitize and store execution summaries.
- Record actor, incident, policy, target, timestamps, and outcome.
- Provide a dry-run mode.

Execution channel:

- Actions on a monitored host are executed by an agent-side executor, not by the backend. The backend never connects into hosts.
- Flow: an authorized user (or policy) creates an execution request; if approval is required, an authorized user approves it; the target agent retrieves pending approved requests for its own identity over its authenticated connection (polling is acceptable); the agent checks the action identifier against its local allowlist, runs it with a timeout, and reports a sanitized result.
- The allowlist and the commands it maps to live only in the agent's local configuration, set by the host administrator. An action that is not in that local allowlist is rejected by the agent and recorded as rejected, even if the backend sent it.
- The agent runs with the least privilege needed for its allowlisted actions. Document any required sudo, systemd, or Docker permissions explicitly, and get approval before changing host configuration.
- If this channel is not implemented, deliver recommendation-only mode and state that clearly in `PROJECT_STATUS.md`.

For the first MVP, a recommendation/manual-action workflow is acceptable. Do not claim automated recovery is implemented unless it has actually executed and been safely verified.

---

# 17. Database design

Use PostgreSQL, SQLAlchemy, and Alembic. The AI must finalize exact types, constraints, and relationships and record important schema decisions.

## 17.1 Users

- `id` UUID primary key.
- `email` unique.
- `password_hash`.
- `role`: `ADMIN`, `OPERATOR`, or `VIEWER`.
- `is_active`.
- `created_at`, `updated_at`.

## 17.2 Agents

- `id` UUID primary key.
- `name`, `hostname`, `os_type`, `agent_version`.
- `credential_hash`.
- `status`.
- `last_heartbeat`.
- `created_at`, `revoked_at`.

## 17.3 Metric records

- Primary key (`BIGINT` or UUID).
- `agent_id` foreign key.
- UTC timestamp.
- CPU usage.
- Memory usage.
- Disk and network measurements.
- Validated metadata (`JSONB` where justified).

The AI must decide whether disk and network measurements belong in normalized child tables or JSONB, based on query requirements. Record the reasoning. Do not discard per-interface or per-filesystem data just to simplify the schema.

## 17.4 Alert rules

- ID, name, metric key, operator, threshold, severity.
- Evaluation window, consecutive breaches, cooldown.
- Optional dimension filter and aggregation mode.
- Enabled flag, timestamps.

## 17.5 Incidents

- ID, agent ID, alert-rule ID.
- Title, description, severity, status.
- Dimension (nullable).
- First detected and last seen timestamps.
- Acknowledged/resolved user references.
- Resolved timestamp.

## 17.6 Incident events

- ID, incident ID, event type, message.
- Actor ID (nullable for system events).
- Timestamp and metadata.

## 17.7 Recovery policies and executions

Policies: ID, name, alert-rule reference, allowlisted action type, target, approval requirement, enabled flag.

Executions: ID, policy ID, incident ID, target agent ID, requested-by and approved-by user IDs, status (`PENDING_APPROVAL`, `APPROVED`, `DISPATCHED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `REJECTED`, `EXPIRED`), start/end timestamps, sanitized output summary.

## 17.8 Metric aggregates

- `id`.
- `agent_id` foreign key.
- `metric_key`.
- `dimension` (nullable; mount point or interface).
- `bucket_start` (UTC) and `bucket_size` (for example 1 minute, 5 minutes, 1 hour).
- `min_value`, `max_value`, `avg_value`, `sample_count`.

Unique constraint on `(agent_id, metric_key, dimension, bucket_start, bucket_size)` so downsampling is idempotent; handle the nullable `dimension` correctly in that rule. Written by the scheduled downsampling task from Section 11.1, retained 30 days by default, and used for dashboard queries over longer time ranges.

## 17.9 Processed batches

- `id`.
- `agent_id` foreign key.
- `batch_id`.
- `status`: `RECEIVED`, `PROCESSING`, `PROCESSED`, or `FAILED`.
- `attempt_count`.
- `received_at`, `processed_at`.
- `error_summary` (sanitized).

Unique constraint on `(agent_id, batch_id)`. The worker uses it to detect duplicate task delivery and agent resends. Clean it up on a bounded schedule that is at least as long as the agent's maximum resend window.

## 17.10 Audit logs

- `id`.
- `actor_user_id` (nullable) and `actor_agent_id` (nullable).
- `action`.
- `target_type`, `target_id`.
- `metadata` (`JSONB`; safe values only, never secrets).
- `created_at`.

Record at least: logins, logouts, and failed logins; first-Admin bootstrap; user creation, role changes, and deactivation; agent provisioning, rotation, and revocation; alert-rule changes; recovery policy changes and execution requests/approvals. Retain under an explicit policy recorded in `DECISION_LOG.md`. Metric retention cleanup must never delete audit logs. Read through `GET /audit-logs` (Admin only).

Add appropriate foreign keys, constraints, indexes, and Alembic migrations. Use UTC timestamps consistently.

---

# 18. REST API plan

Base prefix: `/api/v1`. The AI may refine route names and response envelopes, but it must document the final OpenAPI contract and keep the frontend consistent with it.

## Authentication

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

`POST /auth/register` is not a public endpoint. It is Admin-only and is how Admins create users and assign roles. The first Admin is created by a documented seed/CLI bootstrap command that reads credentials from environment variables. Never commit a default password.

## Users (Admin only)

- `GET /users`
- `GET /users/{id}`
- `PATCH /users/{id}` — role, active status, name.

Prefer deactivation over deletion. Record changes in the audit log.

## Agents

- `POST /agents/register`
- `GET /agents`
- `GET /agents/{id}`
- `PATCH /agents/{id}`
- `DELETE /agents/{id}` — define whether this revokes or deactivates.
- `POST /agents/{id}/rotate-credential` — returns the new secret once and invalidates the old one (after a documented grace period, if any).
- `POST /agents/heartbeat`

## Metrics

- `POST /metrics/ingest`
- `GET /metrics/{agent_id}`
- `GET /metrics/{agent_id}/latest`
- `GET /metrics/{agent_id}/summary`

Support bounded time filters, metric selection, pagination, and sensible maximum limits.

## Alert rules

- `POST /alerts/rules`
- `GET /alerts/rules`
- `GET /alerts/rules/{id}`
- `PATCH /alerts/rules/{id}`
- `DELETE /alerts/rules/{id}`

## Incidents

- `GET /incidents`
- `GET /incidents/{id}`
- `POST /incidents/{id}/acknowledge`
- `POST /incidents/{id}/resolve`
- `POST /incidents/{id}/reopen`
- `POST /incidents/{id}/notes`
- `GET /incidents/{id}/events`

## Recovery

- `POST /recovery/policies`
- `GET /recovery/policies`
- `PATCH /recovery/policies/{id}`
- `POST /recovery/{id}/execute`
- `GET /recovery/executions`
- `GET /agents/commands` — agent-authenticated; returns approved pending execution requests for the calling agent only (Section 16).
- `POST /agents/commands/{id}/result` — agent-authenticated; reports a sanitized outcome.

## Audit

- `GET /audit-logs` — Admin only; filter by actor, action, target, and time; paginated.

Enforce authentication, role permissions, input validation, size/rate limits where appropriate, and consistent error responses.

---

# 19. Target repository structure

```text
opspulse/
├── spec.md
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── workers/
│   │   ├── websocket/
│   │   ├── database/
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── agent/
│   ├── opspulse_agent/
│   │   ├── collectors/
│   │   ├── client/
│   │   ├── config.py
│   │   ├── scheduler.py
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── features/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── store/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
├── simulator/
│   ├── docker/
│   ├── scenarios/
│   └── scripts/
├── docs/
│   ├── PROJECT_STATUS.md
│   ├── DAILY_PROGRESS.md
│   ├── DECISION_LOG.md
│   ├── IMPLEMENTATION_LOG.md
│   ├── TEST_REPORT.md
│   ├── KNOWN_ISSUES.md
│   ├── ARCHITECTURE.md
│   └── DEVELOPMENT_HANDOFF.md
├── .github/
│   └── workflows/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

Create directories as needed. Do not create empty boilerplate folders without a purpose.

---

# 20. Local development and deployment

## 20.1 Environment

Target tools:

- Ubuntu 24.04 or compatible Linux.
- Python 3.12+.
- Node.js LTS and npm.
- Docker Engine.
- Docker Compose plugin.
- Git.

The AI must inspect actual installed versions before recommending changes. It must not install or remove host software without explaining the impact and receiving approval.

## 20.2 Docker Compose services

Expected local services:

- PostgreSQL.
- Redis.
- FastAPI backend.
- Celery worker.
- Celery Beat only if scheduled tasks require it.
- React frontend.

Run the host monitoring agent directly on Ubuntu at first so it can observe host resources. Add container agents for simulated hosts later.

Example development ports (configurable):

| Service | Port |
|---|---:|
| Frontend | 5173 |
| FastAPI | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |

Use health checks, dependency readiness, persistent database volumes, and non-secret environment examples. Do not expose PostgreSQL or Redis publicly in a production deployment.

---

# 21. Testing and simulation plan

Testing is required throughout development, not only at the end.

## 21.1 Unit tests

Agent tests:

- CPU collector.
- Memory collector.
- Disk collector.
- Network collector and counter deltas.
- Payload serialization.
- Retry/backoff.
- Configuration validation.

Backend tests:

- Authentication and authorization.
- Agent credential verification.
- Metric validation and idempotency.
- Alert operators and evaluation windows.
- Incident deduplication and state transitions.
- Heartbeat state transitions.
- Recovery allowlist validation.

## 21.2 Integration tests

- FastAPI with PostgreSQL.
- FastAPI with Redis.
- Celery with Redis.
- Worker persistence to PostgreSQL.
- Alert engine with incident service.
- WebSocket event publishing and authentication.

Use isolated test databases/containers. Tests must not modify the user's real monitoring data.

## 21.2A Frontend tests

Use Vitest and React Testing Library for components, and Playwright for the end-to-end flow.

- Forms and tables, including alert-rule validation errors and incident actions.
- Loading, empty, and error states.
- Route protection and role-based UI.
- API error handling.
- WebSocket reconnect and REST refresh fallback (mocked).
- One Playwright flow: log in, see real backend data on the Overview page, and see an incident appear after a threshold breach.

## 21.3 End-to-end pipeline

Verify the complete flow:

`Agent → FastAPI → Redis → Celery Worker → PostgreSQL → Alert Engine → Incident → Dashboard`

## 21.4 Required simulation scenarios

### A. CPU spike

Generate bounded CPU load using a dedicated script/container.

Expected: the agent reports increased CPU; backend stores metrics; configured threshold/window is crossed; an incident is created and appears on the dashboard.

### B. Memory pressure

Use a bounded memory test with a strict maximum allocation and cleanup.

Expected: memory utilization rises and the alert triggers if threshold/window criteria are met. Never allocate unbounded memory on the host.

### C. Disk pressure

Use a dedicated temporary directory or Docker volume with a strict size limit.

Expected: usage rises and the alert triggers. Never fill the host root filesystem.

### D. Agent disconnection

Stop an agent.

Expected: heartbeats stop; agent becomes degraded and then offline according to thresholds; one deduplicated offline incident is created.

### E. Backend unavailable

Stop FastAPI temporarily.

Expected: agent retries; local buffer remains bounded; metrics are resent when service returns; duplicate batches are handled safely.

### F. Redis unavailable

Stop Redis.

Expected: API does not falsely acknowledge queue acceptance; agent retries; processing resumes after recovery.

### G. Recovery workflow

Use a disposable test service/container and an allowlisted action.

Expected: policy and permission are checked; action executes only on configured target; result is recorded; unauthorized actions are rejected.

### H. PostgreSQL unavailable

Stop PostgreSQL temporarily.

Expected: the behavior is documented and matches reality. Agent credential checks need PostgreSQL, so ingestion is expected to fail fast with a clear 503 and the agent retries within its bounded buffer. Tasks already queued are not lost (retried with bounded backoff). After recovery, processing resumes with no duplicate metrics or incidents, and the readiness endpoint reports the degraded state while the database is down.

---

# 22. Non-functional requirements

## Performance

Initial values are targets to measure, not promises:

- Agent collection interval: 10 seconds.
- Heartbeat interval: 30 seconds.
- Dashboard updates: near real time.
- Configurable batch size.
- Bounded ingestion and processing latency.
- Agent resource overhead measured under idle and load.

Record actual measurements and environment details. Never invent benchmark numbers.

## Reliability

- Bounded retries and buffering.
- Idempotent processing.
- Database transactions.
- Observable worker failures.
- Graceful shutdown.
- Reconnection behavior.
- Clear degraded-service behavior.

## Security

- Secure password and credential hashing.
- Role-based access control.
- Authenticated agent endpoints.
- Authenticated WebSockets.
- Request size/rate limits where appropriate.
- Secrets kept outside Git.
- No secret logging.
- Restricted recovery actions.
- Audit history.
- HTTPS for remote deployment.

## Maintainability

- Type hints.
- Small, cohesive modules.
- Pydantic request/response schemas.
- Alembic migrations.
- Structured logging.
- Consistent error handling.
- Unit and integration tests.
- Updated documentation.
- CI running lint, type checks, and tests on every push.

---

# 23. 30-day implementation roadmap

The roadmap is a sequence, not permission to skip quality gates. If a day is incomplete, carry the work forward and update the schedule honestly.

## Phase 1 — Foundation

### Day 1: Repository and environment
- Inspect OS and tool versions.
- Initialize Git and repository structure.
- Create `.gitignore` and `.env.example`.
- Create required documentation files.
- Write initial architecture and project status.
- Verify Python environment and Git.

**Deliverable:** Reproducible project skeleton and documented plan.

### Day 2: FastAPI skeleton
- Create FastAPI application.
- Add settings/configuration.
- Add health endpoint.
- Configure logging.
- Add pytest, lint, and type-check configuration.
- Add a GitHub Actions workflow that runs lint, type checks, and tests; extend it as components are added.

**Deliverable:** Running, tested API skeleton.

### Day 3: Database foundation
- Configure PostgreSQL.
- Integrate SQLAlchemy.
- Configure Alembic.
- Add only the initial schema justified by the current phase.
- Verify migration up/down in a disposable test database.

**Deliverable:** Verified database connection and migrations.

## Phase 2 — Monitoring agent

### Day 4: CPU collector
- Implement CPU metrics.
- Handle first sampling interval.
- Add unit tests.

### Day 5: Memory collector
- Implement RAM and swap metrics.
- Add validation and tests.

### Day 6: Disk and network collectors
- Collect filesystems and network counters.
- Calculate rates from counter deltas.
- Handle missing interfaces and counter resets.
- Add tests.

### Day 7: Agent runtime
- Add configuration.
- Add scheduler.
- Add payload schema.
- Add logging and graceful shutdown.
- Verify local collection.

**Deliverable:** Functional Ubuntu monitoring agent.

## Phase 3 — Identity and ingestion

### Day 8: Agent provisioning
- Agent model and migration.
- User model and migration, login/logout/current-user endpoints, first-Admin bootstrap command, and Admin-only user creation and role assignment.
- Audit-log table and writer for security-relevant actions (Section 17.10).
- Secure credential generation and hashing.
- Provisioning, rotation, and revocation flow.
- Tests.

### Day 9: Heartbeat and ingestion API
- Agent authentication dependency.
- Heartbeat endpoint.
- Metric batch validation.
- Request size limits.
- API tests.

### Day 10: Queue and worker
- Redis and Celery configuration.
- Queue metric batches.
- Worker skeleton.
- Retry and idempotency implementation.
- Integration tests.

**Deliverable:** Agent can submit authenticated metric batches to an asynchronous pipeline.

## Phase 4 — Storage and alerts

### Day 11: Metric persistence
- Metric schema and migration.
- Persist batches.
- Add indexes.
- Latest/history query endpoints.
- Retention cleanup and downsampling tasks (Section 11.1) writing `metric_aggregates`.
- Tests.

### Day 12: Alert-rule management
- Rule model and validation.
- CRUD endpoints.
- Authorization.
- Tests.

### Day 13: Alert evaluation
- Comparison operators.
- Evaluation windows.
- Consecutive breaches.
- Missing-data behavior.
- Tests.

### Day 14: Alert reliability
- Cooldowns.
- Deduplication.
- Recovery/clear condition.
- Repeated-breach tests.

**Deliverable:** Configurable alert engine backed by stored metrics.

## Phase 5 — Incidents and agent health

### Day 15: Incident creation
- Incident and event models.
- Creation/list/detail services.
- Connect alert engine to incident service.

### Day 16: Incident lifecycle
- Acknowledge and investigate.
- Resolve and reopen.
- Record event history.
- Enforce allowed state transitions.

### Day 17: Agent health
- Heartbeat monitoring.
- Degraded/offline detection.
- Offline incident deduplication.
- Recovery when agent returns.

**Deliverable:** Complete incident lifecycle and agent health monitoring.

## Phase 6 — Frontend

### Day 18: Frontend setup
- Initialize React and TypeScript.
- Configure Vite and Tailwind.
- Configure routing and state approach.
- Create dashboard layout.

### Day 19: Overview
- Build overview page.
- Display agent and incident statistics.
- Integrate backend APIs.

### Day 20: Infrastructure
- Build infrastructure listing.
- Build machine detail page.
- Add CPU, memory, disk, and network charts.

### Day 21: Incident dashboard
- Display incidents.
- Add filters and detail view.
- Add incident actions.

### Day 22: Alert rules and realtime
- Build alert-rule interface.
- Integrate authenticated WebSockets.
- Handle reconnection and fallback refresh.

**Deliverable:** Functional dashboard connected to real backend data.

## Phase 7 — Recovery and simulation

### Day 23: Recovery policies
- Design recovery policy model.
- Implement allowlisted action registry.
- Add permission checks, dry-run, and execution history.
- Implement the agent-side executor and polling channel (Section 16), or deliver recommendation-only mode.
- If safe execution cannot be completed, deliver manual recommendations and document the limitation.

### Day 24: Docker simulation
- Create simulated monitoring environments.
- Configure multiple agents.
- Build bounded CPU, memory, and disk scenarios.

### Day 25: Failure testing
- Test agent disconnection.
- Test backend unavailability.
- Test Redis failure.
- Test PostgreSQL failure.
- Test recovery workflow where implemented.
- Verify incident generation.

**Deliverable:** Locally testable distributed monitoring environment.

## Phase 8 — Hardening and finalization

### Day 26: Integration testing
- Test ingestion pipeline.
- Test alert-to-incident workflow.
- Test authentication and authorization.
- Test failure handling.
- Run frontend component tests and the core Playwright end-to-end flow.

### Day 27: Reliability and bug fixing
- Improve retries and error handling.
- Improve logs.
- Fix high-priority bugs.
- Update known issues.

### Day 28: Docker deployment
- Finalize Dockerfiles and Compose.
- Verify clean startup and shutdown.
- Verify persistent data behavior.
- Document deployment.

### Day 29: Benchmarking
Measure:
- Ingestion latency.
- Processing latency.
- End-to-end latency.
- Metrics throughput.
- Agent CPU and memory overhead.
- Failure detection time.

Record environment and test method with every result.

### Day 30: Finalization
- Finalize README and architecture docs.
- Verify acceptance criteria.
- Capture real screenshots.
- Record a demonstration.
- Verify repository cleanliness and setup from a clean checkout.
- Prepare final project report.

**Deliverable:** Documented, tested, reproducible local project.

---

# 24. Acceptance criteria and definition of done

The MVP is complete only when the following are verified:

- [ ] Ubuntu monitoring agent runs.
- [ ] CPU metrics are collected correctly.
- [ ] Memory and swap metrics are collected correctly.
- [ ] Disk metrics are collected correctly.
- [ ] Network counters/rates are collected correctly.
- [ ] Agent credentials are provisioned and authenticated.
- [ ] Agent credentials can be rotated and revoked.
- [ ] Heartbeats are accepted and agent status changes correctly.
- [ ] First-Admin bootstrap and Admin-only user management work.
- [ ] Metric batches reach FastAPI.
- [ ] Queue acceptance is handled correctly.
- [ ] Celery workers process batches.
- [ ] Metrics persist in PostgreSQL.
- [ ] Historical metric queries work.
- [ ] Alert rules can be configured.
- [ ] Threshold breaches create incidents.
- [ ] Duplicate incidents are prevented.
- [ ] Agent disconnection is detected.
- [ ] Incident lifecycle and event history work.
- [ ] Dashboard displays real backend data.
- [ ] WebSocket updates work with authentication and reconnect behavior.
- [ ] Docker Compose starts required services.
- [ ] CPU, memory, disk, and failure simulations work safely.
- [ ] Automated tests pass for implemented MVP functionality.
- [ ] Frontend component tests and the core end-to-end flow pass.
- [ ] CI runs lint, type checks, and tests.
- [ ] Documentation is complete and accurate.
- [ ] A clean local deployment is reproducible.

Recovery automation is an advanced milestone and must be independently verified. Do not mark the MVP complete solely because all planned days have elapsed.

---

# 25. Final engineering rules for the AI

1. Correctness before speed.
2. Reliability before visual polish.
3. Tested implementation before feature claims.
4. Simple architecture before unnecessary complexity.
5. Security before recovery automation.
6. Documentation throughout development, not only at the end.
7. Explain important decisions and trade-offs in plain language.
8. Keep the user informed at meaningful milestones.
9. Do not silently begin the next development day.
10. Preserve prior progress and decision history.
11. Never fabricate test results, metrics, or benchmarks.
12. Never expose credentials or commit secrets.
13. Never run destructive host commands or install/remove host software without approval.
14. Use bounded, reversible test simulations.
15. If the implementation differs from this specification, document why and obtain approval for material changes.

**Final outcome:** A developer must be able to clone the repository, start the platform using Docker Compose, run an agent on a real Ubuntu host and simulated machines, generate controlled infrastructure failures, and observe metrics, alerts, and incidents through the dashboard without paid cloud infrastructure.

**End of specification.**
