# OpsPulse — Known Issues

> Track every unresolved issue. Close issues when fixed with resolution date.

---

## KI-001 — Python 3.14 Installed (Spec Requires 3.12+)
**Severity:** LOW  
**Status:** MONITORING  
**Date Discovered:** 2026-11-05  
**Module:** Environment / All Python code  

### Summary
Ubuntu 26.04 ships with Python 3.14.4. The spec requires Python 3.12+. 3.14 satisfies the minimum requirement but is newer than what most package wheels are tested against.

### Expected Behavior
All backend and agent Python packages install cleanly and function correctly.

### Actual Behavior
Potential risk: some packages (especially those with C extensions like `psycopg2-binary`) may not have wheels for Python 3.14 yet, requiring compilation from source, which may fail or be slow.

### Workaround
- Use `asyncpg` instead of `psycopg2-binary` for the async backend (wheels more likely available).
- For Celery sync workers, use `psycopg2-binary` and fall back to source build if needed.
- Monitor `pip install` output during Day 2 for any failed wheel downloads.

### Next Action
Attempt `pip install -r requirements.txt` on Day 2. Document any failures here.

---

## KI-002 — pip Not Available at System Level
**Severity:** LOW  
**Status:** RESOLVED (workaround in place)  
**Date Discovered:** 2026-11-05  
**Module:** Environment / Developer setup  

### Summary
`python3 -m pip` returns "No module named pip" on the host system. This is Ubuntu 26.04 policy (pip is not included in the base Python installation to avoid system-wide package pollution).

### Workaround
Use `python3 -m venv <dir> --upgrade-deps` which bootstraps pip inside the virtual environment using `ensurepip`. All package operations happen inside the venv.

### Resolution Date
2026-11-05 — Workaround documented and confirmed working. `python3 -m venv --help` confirms venv module is available.

---

*New issues will be appended above as discovered.*
