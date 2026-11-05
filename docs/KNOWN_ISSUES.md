# OpsPulse — Known Issues

> Track every unresolved or resolved issue with root cause and workaround.

---

## KI-001 — Host Python 3.14 Lacks Binary Wheels for C-Extension Packages
**Severity:** MEDIUM  
**Status:** RESOLVED (via Containerization)  
**Date Discovered:** 2026-11-05  
**Resolution Date:** 2026-11-05  
**Module:** Backend Environment / Tooling  

### Summary
Ubuntu 26.04 ships with Python 3.14.4. Essential backend packages (`pydantic-core`, `asyncpg`, `psycopg2-binary`) fail to install on host because pre-built wheels do not exist for Python 3.14, and source builds require bleeding-edge rust/maturin tooling.

### Expected Behavior
`pip install -r requirements.txt` succeeds and builds all required wheels.

### Actual Behavior
`pip install` fails with `Failed to build asyncpg pydantic-core psycopg2-binary`.

### Resolution / Workaround
Implemented multi-stage Docker build using official `python:3.12-slim` base image (`backend/Dockerfile`). All backend execution, tests, linting, and typing run inside this container using Docker Compose and Docker CLI (`docker run --rm -v $(pwd)/backend:/app opspulse-backend:test`). See DEC-009.

---

## KI-002 — Host Missing System-Level `pip`
**Severity:** LOW  
**Status:** RESOLVED (via Virtualenv & Containerization)  
**Date Discovered:** 2026-11-05  
**Resolution Date:** 2026-11-05  
**Module:** Environment / Developer Setup  

### Summary
`python3 -m pip` returned `No module named pip` on the Ubuntu 26.04 host.

### Resolution
Resolved by using `python3 -m venv --upgrade-deps` for venv creation where needed, and relying on containerized environments for the backend service.
