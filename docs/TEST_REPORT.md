# OpsPulse — Test Report

> Cumulative test history. Never call "no tests collected" a passing suite.
> Never claim a command was run if it was not.

---

## Test Run: TR-001
**Date:** 2026-11-05  
**Run ID:** Day-1-environment-audit  
**Phase:** Pre-code audit  

### Commands
```
(No application tests exist yet — no code has been written)
```

### Result
- **Passed:** 0
- **Failed:** 0
- **Skipped:** 0
- **Not collected:** 0
- **Status:** NOT APPLICABLE — no test code exists

### Notes
Day 1 is the planning and scaffolding day. No application code or tests are expected. The first tests will be written alongside the FastAPI skeleton in Day 2 and the agent collectors in Days 4–6.

---

*Test runs will be appended here as development progresses.*



---

## Test Run: TR-002
**Date:** 2026-11-05  
**Run ID:** Day-2-fastapi-skeleton  
**Phase:** Phase 1 — Foundation  

### Commands
```bash
docker run --rm -v $(pwd)/backend:/app opspulse-backend:test ruff check app/ tests/
docker run --rm -v $(pwd)/backend:/app opspulse-backend:test ruff format --check app/ tests/
docker run --rm -v $(pwd)/backend:/app opspulse-backend:test mypy app/
docker run --rm -v $(pwd)/backend:/app opspulse-backend:test pytest -v
curl http://localhost:8000/api/v1/health
```

### Result
- **Passed:** 4 unit tests (`test_health_returns_200`, `test_health_returns_ok_status`, `test_health_returns_version`, `test_health_response_schema`)
- **Failed:** 0
- **Skipped:** 0
- **Not collected:** 0
- **Linter Status:** Ruff check clean (0 errors)
- **Formatter Status:** Ruff format clean (18 files checked)
- **Type Checker Status:** Mypy clean (0 errors across 16 source files)
- **Live Smoke Test:** HTTP 200 `{"status":"ok","version":"0.1.0"}`

### Notes
All tests executed inside the Python 3.12 container environment with full isolation.


---

## Test Run: TR-003
**Date:** 2026-11-05  
**Run ID:** Day-3-database-foundation  
**Phase:** Phase 1 — Foundation (Database Tier)

### Commands
```bash
docker run --rm --network opspulse_default -e POSTGRES_HOST=opspulse-postgres -e POSTGRES_PASSWORD=CHANGE_ME -v $(pwd)/backend:/app opspulse-backend:test alembic upgrade head
docker run --rm --network opspulse_default -e POSTGRES_HOST=opspulse-postgres -e POSTGRES_PASSWORD=CHANGE_ME -v $(pwd)/backend:/app opspulse-backend:test alembic downgrade base
docker run --rm --network opspulse_default -e POSTGRES_HOST=opspulse-postgres -e POSTGRES_PASSWORD=CHANGE_ME -v $(pwd)/backend:/app opspulse-backend:test alembic upgrade head
docker run --rm --network opspulse_default -e POSTGRES_HOST=opspulse-postgres -e POSTGRES_PASSWORD=CHANGE_ME -v $(pwd)/backend:/app opspulse-backend:test ruff check app/ tests/
docker run --rm --network opspulse_default -e POSTGRES_HOST=opspulse-postgres -e POSTGRES_PASSWORD=CHANGE_ME -v $(pwd)/backend:/app opspulse-backend:test ruff format --check app/ tests/
docker run --rm --network opspulse_default -e POSTGRES_HOST=opspulse-postgres -e POSTGRES_PASSWORD=CHANGE_ME -v $(pwd)/backend:/app opspulse-backend:test mypy app/ tests/
docker run --rm --network opspulse_default -e POSTGRES_HOST=opspulse-postgres -e POSTGRES_PASSWORD=CHANGE_ME -e TESTING=true -v $(pwd)/backend:/app opspulse-backend:test pytest -v
curl http://localhost:8000/api/v1/health
```

### Result
- **Passed:** 8 unit & integration tests
  - `tests/test_database.py::test_database_health_check` (PASSED)
  - `tests/test_database.py::test_create_and_query_user` (PASSED)
  - `tests/test_database.py::test_user_email_unique_constraint` (PASSED)
  - `tests/test_database.py::test_create_and_update_agent` (PASSED)
  - `tests/test_health.py::test_health_returns_200` (PASSED)
  - `tests/test_health.py::test_health_returns_ok_or_degraded` (PASSED)
  - `tests/test_health.py::test_health_returns_version` (PASSED)
  - `tests/test_health.py::test_health_response_schema` (PASSED)
- **Failed:** 0
- **Skipped:** 0
- **Execution Time:** 0.85s
- **Linter Status:** Ruff check clean (0 errors)
- **Formatter Status:** Ruff format clean (24 files checked)
- **Type Checker Status:** Mypy clean (0 errors across 24 source files)
- **Migration Status:** Full upgrade/downgrade/re-upgrade verified
- **Live Smoke Test:** HTTP 200 `{"status":"ok","version":"0.1.0","database":"ok"}`


---

## Test Run: TR-004
**Date:** 2026-11-05  
**Run ID:** Day-4-agent-cpu-collector  
**Phase:** Phase 2 — Monitoring Agent

### Commands
```bash
cd agent && .venv/bin/pytest -v
cd agent && .venv/bin/ruff check opspulse_agent/ tests/
cd agent && .venv/bin/ruff format --check opspulse_agent/ tests/
cd agent && .venv/bin/mypy opspulse_agent/ tests/
docker run --rm --network opspulse_default -e POSTGRES_HOST=opspulse-postgres -e POSTGRES_PASSWORD=CHANGE_ME -e TESTING=true -v $(pwd)/backend:/app opspulse-backend:test pytest -v
```

### Result
- **Agent Unit Tests:** 4 passed in 0.21s
  - `tests/test_cpu_collector.py::test_cpu_collector_live_collection` (PASSED)
  - `tests/test_cpu_collector.py::test_cpu_collector_mocked_values` (PASSED)
  - `tests/test_cpu_collector.py::test_cpu_collector_graceful_missing_freq_and_loadavg` (PASSED)
  - `tests/test_cpu_collector.py::test_cpu_metrics_pydantic_schema_validation` (PASSED)
- **Backend Tests:** 8 passed in 1.01s
- **Total Suite Passing:** 12 tests across repo
- **Linter Status:** Ruff check clean (0 errors)
- **Formatter Status:** Ruff format clean (all files)
- **Type Checker Status:** Mypy strict clean (0 issues)
- **Live Smoke Test:** Verified real host metrics (12 logical cores, 6 physical cores, 3368.6 MHz, 4.31 loadavg)
