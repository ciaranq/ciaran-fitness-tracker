# TASK_GRAPH.md: Directed Acyclic Execution Graph (DAG)

## Node Registry & Status
- **[COMPLETED] G01: Workspace Hardening**
  - Scope: Monorepo layout, Bun runtime, UV venv, Git baseline.
- **[COMPLETED] [AGY] G02: Ingest Schema Parser & Contracts**
  - Depends On: G01
  - Targets: `backend/ingestion/contracts.py`, `backend/tests/test_contracts.py`
  - Exit Gate: `uv run pytest backend/tests/` passes.
- **[COMPLETED] [AGY] G03: Frontend Skeleton & Tailwind System**
  - Depends On: G01
  - Targets: `frontend/src/app/`, `frontend/src/components/`
  - Exit Gate: `bun run build` exits 0 with zero TypeScript errors.
- **[COMPLETED] [Claude] G04: DuckDB & SQLite Layer**
  - Depends On: G02
  - Targets: `backend/engine/db.py`
- **[READY] [AGY] G05: File Watcher Hot-Folder Loop**
  - Depends On: G02
  - Targets: `backend/ingestion/watcher.py`
- **[READY] [Claude] G06: Periodization & Recovery Engine**
  - Depends On: G04
  - Targets: `backend/engine/planner.py`
- **[BLOCKED] [AGY] G07: Google Workspace Bi-directional Sync**
  - Depends On: G06
  - Targets: `backend/integrations/google_tasks.py`, `backend/integrations/google_calendar.py`
- **[READY] [AGY] G08: Glassmorphic Biometric HUD**
  - Depends On: G03, G04
  - Targets: `frontend/src/components/vitals/`
- **[BLOCKED] [Claude + AGY] G09: End-to-End Canary Release**
  - Depends On: G07, G08
