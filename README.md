# OpsPulse

**Distributed Infrastructure Monitoring & Incident Management Platform**

> Local-first, Docker Compose–based, AI-assisted incremental development.

---

## What is OpsPulse?

OpsPulse collects system metrics (CPU, memory, disk, network) from monitored Linux hosts via lightweight agents, transports them to a central FastAPI backend, processes them asynchronously with Celery workers, evaluates configurable alert rules, manages incidents, and displays real-time infrastructure health in a React dashboard.

## Stack

| Layer | Technology |
|---|---|
| Agent | Python 3.14, psutil |
| Backend | FastAPI, SQLAlchemy 2.x, Alembic |
| Database | PostgreSQL |
| Queue/Worker | Redis, Celery |
| Frontend | React + TypeScript, Vite, Tailwind CSS, Recharts |
| Realtime | FastAPI WebSockets |
| Deployment | Docker Compose |
| Testing | Pytest, Vitest, Playwright |

## Quick Start (once implemented)

```bash
# 1. Clone repository
git clone <repo-url> opspulse
cd opspulse

# 2. Copy and configure environment
cp .env.example .env
# Edit .env with real secrets

# 3. Start infrastructure
docker compose up -d

# 4. Bootstrap first admin
docker compose exec backend python -m app.cli seed-admin

# 5. Run host agent (outside Docker, on this machine)
cd agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export AGENT_SECRET=<secret-from-provisioning>
python -m opspulse_agent.main --config config.yaml

# 6. Open dashboard
open http://localhost:5173
```

## Project Status

See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).

## Documentation

| File | Purpose |
|---|---|
| [spec.md](spec.md) | Full project specification |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture and data flows |
| [docs/DAILY_PROGRESS.md](docs/DAILY_PROGRESS.md) | Append-only development journal |
| [docs/DECISION_LOG.md](docs/DECISION_LOG.md) | Engineering decisions |
| [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) | Open issues |
| [docs/DEVELOPMENT_HANDOFF.md](docs/DEVELOPMENT_HANDOFF.md) | Session continuity |

## Development

Refer to `spec.md` Section 20 for environment requirements and Section 23 for the 30-day roadmap.

---

*Development start: 2026-11-05*
