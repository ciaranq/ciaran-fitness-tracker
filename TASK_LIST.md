# TASK_LIST.md: Multi-Agent Execution Checklist

Synchronized with `TASK_GRAPH.md` and GitHub Issues (`#1`–`#6`). Every task carries an explicit owner tag (`[Claude]`, `[AGY]`, `[Gemini]`).

## Phase 1: Foundation & Verification Gates (Issue #1)
- [x] `[Gemini]` Draft initial architecture specs, DAG (`TASK_GRAPH.md`), state machine (`STATE_MACHINE.md`), and monorepo generator (`bundel.py`).
- [x] `[AGY]` **G01: Workspace Hardening** — unpack monorepo tree, data ingest directories, and root configs.
- [x] `[AGY]` **G02: Ingest Schema Parser & Contracts** — configure Hatchling wheel discovery in `backend/pyproject.toml` and verify Pydantic contracts (`BloodPressureReading`, `SpirometryReading`, `ActivitySummary`) via `uv run --directory backend pytest` (`3 passed`).
- [x] `[AGY]` **G03: Frontend Skeleton & Tailwind System** — install dependencies via `bun install --cwd frontend` and verify production build via `bun run --cwd frontend build` (`exit 0`).
- [x] `[Claude]` **AUDIT_GATE (G02 & G03)** — review git diff, mark `G02` & `G03` as `[COMPLETED]` in `TASK_GRAPH.md`, and promote `G04` & `G05` to `[READY]`.

## Phase 2: Storage Layer & Hot-Folder Ingestion (Issues #2 & #3)
- [x] `[Claude]` **G04: DuckDB & SQLite Dual-Store Layer (`backend/engine/db.py`)**
  - [x] `[Claude]` Verify/harden `biometrics.duckdb` (`vitals_log`, `activity_summary`) and `app_state.db` (`physio_plans`, `sync_tracking`).
  - [x] `[Claude]` Seed `physio_plans` with the Nov 2, 2026 clinical rehab & asymmetric stretching protocol from `data/physio/physio-notes1.md`.
  - [x] `[Claude]` Add database initialization & seeding tests (`uv run --directory backend pytest`).
- [ ] `[AGY]` **G05: File Watcher Hot-Folder Loop (`backend/ingestion/watcher.py`)**
  - [ ] `[AGY]` Route incoming files in `data/raw/ingest/` (Garmin FIT/JSON, QardioArm BP, Spirometer Peak Flow, Apple Health, Physio notes) through `backend/ingestion/contracts.py`.
  - [ ] `[AGY]` Persist validated records to `biometrics.duckdb` / `app_state.db` and archive raw files to `data/processed/archive/`.
  - [ ] `[AGY]` Add end-to-end watcher ingest tests (`uv run --directory backend pytest`).

## Phase 3: Clinical Periodization & Google Sync (Issues #4 & #5)
- [ ] `[Claude]` **G06: Periodization & Recovery Engine (`backend/engine/planner.py`)**
  - [x] `[Claude]` Implement 6-month Zone 2 aerobic base progression balanced with 3x10 standing band strength blocks.
  - [x] `[Claude]` Enforce clinical contraindications (block seated knee extension & wide-grip lat pull-downs) and symptom-flare circuit breakers.
  - [ ] `[Claude]` Expose FastAPI router endpoints for vitals summary, rehab protocol, and progression state.
- [ ] `[AGY]` **G07: Google Workspace Bi-Directional Sync (`backend/integrations/`)**
  - [ ] `[AGY]` Implement `google_tasks.py` for daily rehab exercise & asymmetric stretch checklists.
  - [ ] `[AGY]` Implement `google_calendar.py` for Zone 2 sessions, strength blocks, and the 2-week physio follow-up checkpoint.
  - [ ] `[AGY]` Reconcile sync state in `app_state.db` (`sync_tracking`).

## Phase 4: Biometric HUD & Canary Release (Issue #6)
- [ ] `[AGY]` **G08: Glassmorphic Biometric HUD (`frontend/src/components/vitals/`)**
  - [ ] `[AGY]` Build interactive vitals cards, Zone 2 progress visuals, and daily physio/stretching adherence panels wired to FastAPI.
- [ ] `[Claude]` `[AGY]` **G09: End-to-End Canary Release**
  - [ ] `[AGY]` Run full frontend production build (`bun run --cwd frontend build`) and E2E verification.
  - [ ] `[Claude]` Perform final `AUDIT_GATE` security, schema, and regression review.

## Phase 5: Nutrition, Supplements & Sauna (Issues #15 & #16)
- [ ] `[Claude]` `[AGY]` **G10: Nutrition & Supplements** — BLOCKED until Issue #15 open questions are approved.
  - [ ] `[Claude]` Schema (SQLite mutable + DuckDB mirror), ingest contract, planner adherence input.
  - [ ] `[AGY]` Logging router + HUD entry form + daily supplement checklist.
- [ ] `[Claude]` `[AGY]` **G11: Sauna** — BLOCKED until Issue #16 open questions are answered (clinician check, Issue #13).
  - [ ] `[Claude]` `sauna_session` schema, planner safety rule (flare / vitals-hold gating).
  - [ ] `[AGY]` Logging router + HUD entry form.
