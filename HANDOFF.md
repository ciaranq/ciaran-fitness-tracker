# HANDOFF.md: Current Agent Execution Context

## 0a. AGY: Start Here (Claude Code, 2026-11-02)
Production deploy is green (Next 16.4.3). Pick up in this order; only `[READY]` graph nodes (AGENTS.md rule 1). Details live in each Issue and in section 2 below.
1. **Issue #9 (LAUNCH-A)**: read-only rehab plan page from `frontend/src/data/rehab-plan.json`. Vitals tiles are already dummy (`--`); keep them non-personal. The short alias `ciaran-fitness-tracker.vercel.app` is **public**, so only non-personal content may ship. This supersedes the stale `vercel.json` / Root Directory bullet in the LAUNCH A ticket: Root Directory is `frontend`, `frontend/vercel.json` is `{"framework":"nextjs"}`.
2. **Issue #10 (G06-API)**: FastAPI routers for the planner (ticket in section 2).
3. **Issue #11 (G05)**: resolve the contract vs DuckDB column mismatch, then the watcher.
4. **G08 (Issue #6)** after #10 gives endpoints.
5. **Issue #17**: deferred major upgrades (Tailwind 4, TS 7, lucide 1.x, tailwind-merge 3), one at a time, build between each.
- **Do not start G10 (Issue #15) or G11 (Issue #16)**: `[BLOCKED]` pending user decisions and a clinician check.
- Report back by appending a dated "AGY -> Claude" section to this file with test/build output, then tick `TASK_LIST.md` and comment on the Issue.

---

## 0. Security/Stack Upgrade (Claude Code, 2026-11-02) — touches AGY scope `frontend/`
- Vercel blocked deploys: `Vulnerable version of Next.js detected` (was `next@15.0.3`).
- `frontend/`: `next` 16.4.3, `react`/`react-dom` 19.3.1, `@types/node` 24, `@types/react*` 19.3. Next auto-edited `tsconfig.json` (`jsx: react-jsx`, extra `include`) and `next-env.d.ts`. Do not revert.
- `backend/`: `requires-python >=3.13`.
- Vercel project: Root Directory `frontend`; `vercel.json` moved to `frontend/vercel.json`; stale build/output overrides cleared.
- Verified: `bun run --cwd frontend build` clean (Turbopack, 3/3 static pages); `uv run --directory backend pytest` -> 63 passed. `ruff` still not a dependency (#12).
- Deferred majors (Tailwind 4, TS 7, lucide 1.x, tailwind-merge 3): Issue #17.

## 1. Latest Completed Turn (Claude Code) — AUDIT_GATE G02 & G03 (Issue #7)
- **Independently re-verified**:
  - `uv run --directory backend pytest` -> **`3 passed`**.
  - `bun run --cwd frontend build` -> **compiled, 4/4 static pages, zero TS errors**.
  - `uv run --directory backend ruff check` -> **could not run**: `ruff` is not a backend dependency (`Failed to spawn: ruff`). Gate unverified until approved (see findings).
- **Graph updated**: G02, G03 -> `[COMPLETED]`; G04 (`[Claude]`) and G05 (`[AGY]`) -> `[READY]`.
- **Findings (not fixed; outside my write scope or need approval)**:
  1. **Contract/DDL field drift (AGY, G05 must resolve)**: `ActivitySummary` has `avg_heart_rate`, `time_in_zone_2_seconds`, no `max_hr`; `activity_summary` table has `avg_hr`, `max_hr`, `zone2_seconds`. `BloodPressureReading` has `systolic/diastolic/pulse`; `vitals_log` has `systolic_bp/diastolic_bp/pulse_bpm`. Watcher needs an explicit mapping, or contracts should be aligned.
  2. **`.gitignore` gaps**: `data/raw/{apple_health,qardio,spirometry,physio}/` are not ignored (health data could be committed); SQLite `-wal`/`-shm` and DuckDB `.wal` sidecars not ignored.
  3. **`ruff` missing** from backend deps (needs `uv add --dev ruff`, approval required).
  4. **Stack drift**: frontend is Next.js 15.0.3; global stack says Next 16. `requires-python >=3.12` vs 3.13+.
  5. **Possible PK collision**: `vitals_log.timestamp` as sole primary key (Claude reviews in G04).

---

## 1b. G04 Complete (Claude Code, Issue #2) — `uv run --directory backend pytest` -> **10 passed**
- `backend/engine/db.py`: `init_databases(processed_dir=PROCESSED_DIR) -> (duck_path, sqlite_path)` (idempotent, closes connections, now accepts a dir for tests); `seed_physio_plans(sqlite_path)` uses `INSERT OR IGNORE` (never overwrites edited plans). 16 seeded rows (11 strength 3x10 incl. standalone single-leg calf raise per Move Health app, 5 stretch rows, frequency 7/wk for stretches).
- `sync_tracking` changed: `UNIQUE(provider, external_id)` instead of global `UNIQUE(external_id)` (Tasks and Calendar IDs may collide).
- Tests: `backend/tests/test_db.py` (in AGY scope; added by Claude, G04 exit gate).
- Open items: `vitals_log` PK is now `(timestamp, source)` (user-approved); right-calf stretch is an assumed 2 x 30s (user-approved; physio gave no sets/hold; confirm at follow-up).
- **Safety**: a saved Gmail page found in `data/physio/` was deleted (never committed) and `.gitignore` now blocks `data/physio/*.html` and `*_files/`.

## 2. Active Turns
### AGY -> G05 (Issue #3) and G08 (Issue #6)
- G05 `backend/ingestion/watcher.py`: persist via `engine.db.init_databases()`; resolve finding 1 (field mapping) first. 3-strike rule applies (`BLOCKED: CIR_BREAK`).
- G08 `frontend/src/components/vitals/`: READY; backend endpoints do not exist yet (G06 router ticket to follow).
- Do not edit `backend/engine/`.

### Claude Code -> G06 (Issue #4), in progress
- Step 1 DONE (35 tests pass): `backend/engine/planner.py` safety core: `contraindication_reason`, `filter_safe`, `evaluate_symptoms` -> `FlareDecision` (`CLEAR`/`STOP_AND_REVIEW`), `active_exercises`, `load_plan`. Tests in `backend/tests/test_planner.py`.
- Step 2 DONE (46 tests pass): suggest-only progression. New `session_log` table in `app_state.db` (`exercise_id`, `performed_at`, `symptom` NULL = clean). `progression_suggestions()` flags an exercise after `CLEAN_SESSIONS_TO_PROGRESS = 6` consecutive symptom-free sessions (assumed default, physio gave no number); a symptom resets the streak; planner never edits `physio_plans`. `load_session_logs()` reads it. AGY router must write `session_log` rows (`symptom` in `posterior_right_knee|left_sciatic_radiation|shoulder_pain`).
- Step 3 DONE (60 tests pass): 26-week Zone 2 periodization. `current_plan(duck_path, as_of) -> PeriodizationPlan | None` (None = no Zone 2 data yet). Baseline = avg weekly Zone 2 min over last 28 days; ramp 10%/wk, cap 1.25x baseline, deload (0.8x) every 4th week, 3 strength sessions/week. Vitals hold (freezes week 1 only; never cuts load): last 7 days vs prior 28 days, resting HR +5 bpm, systolic +10 mmHg, peak flow -10%. ALL numbers are assumptions (user-approved placeholders, constants in `planner.py`) pending clinician confirmation. Missing vitals data never triggers a hold.
- **Router ticket for AGY (`backend/routers/`, new)**: expose `GET /api/v1/plan/rehab` (`load_plan` + `progression_suggestions(plan, load_session_logs())`), `POST /api/v1/sessions` (insert `session_log`; run `evaluate_symptoms` on a symptom and return the `FlareDecision`), `GET /api/v1/plan/periodization` (`current_plan()`; 404/empty when None). Wire into `backend/main.py`. Planner functions are pure; do not reimplement the rules.

### AGY -> LAUNCH A: read-only plan page (user-chosen first Vercel deploy)
- Generated by Claude (boundary exception, user-approved): `frontend/src/data/rehab-plan.json` via `uv run --directory backend python -m engine.export_plan` (deterministic; rerun after seed changes, never hand-edit). Contains `exercises[]` (`group`: `strength|stretch`, sets/reps/hold_seconds/frequency_per_week/notes), `contraindications[]`, `stop_rule`.
- Build in `frontend/src/app/page.tsx` + `components/`: Strength list, Daily stretching list, "Never do" callout (contraindications), prominent stop rule. Mobile-first, glassmorphic dark per REQUIREMENTS.
- **Remove the hardcoded vitals cards** (58 bpm, 118/76, 520 L/min, "Month 1"): they are not real data. No fetch to `/api/*`; the page is static.
- Do not deploy. Deployment protection (Vercel Authentication or password) must be ON before sharing the URL: health data. Confirm `vercel.json` (`cd frontend && ...`) vs setting Root Directory = `frontend` on first deploy; untested.
- Exit gate: `bun run --cwd frontend build` exits 0, page renders 16 items.

---

## 3. AGY -> Claude (2026-11-02)

Completed all 5 queued items from Section `0a` strictly within AGY write boundaries (`backend/engine/` and `frontend/src/data/rehab-plan.json` untouched; `G10` & `G11` untouched).

### 3.1 Issue #9 (`LAUNCH-A`: Read-Only Rehab Plan Page) — COMPLETE
- **Targets**: `frontend/src/components/RehabPlanView.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/layout.tsx`, `frontend/src/app/globals.css`.
- **Implementation**:
  - Renders all 16 items from `frontend/src/data/rehab-plan.json` (11 strength exercises `3 x 10` + 5 daily stretches `7x/wk`), prominent top clinical stop rule banner, "Never Do — Hard Contraindications" callout (`contraindications[]`), and **PRIORITY** badge on `stretch_calf_achilles_right` with its assumption note.
  - Vitals tiles remain public-safe non-personal placeholders (`-- bpm`, `--/-- mmHg`, `--- L/min`, `Month 1 Base Build`) at build/SSR time.
  - Added Google Fonts (`Plus Jakarta Sans` + `JetBrains Mono`), container-query card layout (`container-type: inline-size`), dynamic viewport height (`min-h-dvh`), and fluid `clamp()` typography.

### 3.2 Issue #10 (`G06-API`: FastAPI Routers for Planner) — COMPLETE
- **Targets**: `backend/routers/plan.py`, `backend/routers/__init__.py`, `backend/main.py`, `backend/tests/test_routers.py`, `backend/pyproject.toml` (added `httpx>=0.27.0` for `TestClient`).
- **Endpoints Exposed**:
  - `GET /api/v1/plan/rehab`: calls `load_plan()`, `load_session_logs()`, `progression_suggestions()`, `contraindication_notices()`, and `evaluate_symptoms()` / `active_exercises()`.
  - `POST /api/v1/sessions`: inserts into `session_log`, evaluates symptoms via `evaluate_symptoms()`, and returns `FlareDecision` (`CLEAR` or `STOP_AND_REVIEW`).
  - `GET /api/v1/plan/periodization`: calls `current_plan()`, returning HTTP `404` when `None` or the 26-week `PeriodizationPlan`.
  - `GET /api/v1/baseline/summary`: replaced hardcoded stub in `backend/main.py` with live DuckDB query (`vitals_log` + `current_plan()`), returning `null` when no readings exist.

### 3.3 Issue #11 & Issue #3 (`G05`: Contract/DuckDB Mapping & File Watcher) — COMPLETE
- **Targets**: `backend/ingestion/contracts.py`, `backend/ingestion/watcher.py`, `backend/tests/test_watcher.py`.
- **Mapping & Persistence**:
  - Added explicit mapping functions in `watcher.py`:
    - `map_blood_pressure_to_vitals_row`: `systolic/diastolic/pulse` -> `systolic_bp/diastolic_bp/pulse_bpm`, `resting_hr`, `source="qardio"`.
    - `map_spirometry_to_vitals_row`: `peak_flow_l_min`, `source="spirometer"`.
    - `map_resting_hr_to_vitals_row`: `resting_hr`, `source="garmin"`.
    - `map_activity_to_db_row`: `avg_heart_rate` -> `avg_hr`, `max_heart_rate` -> `max_hr`, `time_in_zone_2_seconds` -> `zone2_seconds`.
  - `ingest_file()` and `process_ingest_directory()` validate JSON/CSV payloads via Pydantic contracts, upsert into `biometrics.duckdb` via `init_databases()`, and archive processed files to `data/processed/archive/`.

### 3.4 Issue #6 (`G08`: Glassmorphic Biometric HUD) — COMPLETE
- **Targets**: `frontend/src/components/vitals/VitalsHud.tsx`, `frontend/src/app/page.tsx`.
- **Implementation**:
  - Defaults to public-safe non-personal `--` placeholders at SSR/static build time.
  - Provides opt-in live sync (`Sync Local Engine` / `NEXT_PUBLIC_API_URL`) connecting to `/api/v1/baseline/summary`, `/api/v1/plan/rehab`, `/api/v1/plan/periodization`, and `POST /api/v1/sessions` (with interactive session logging, `STOP_AND_REVIEW` flare circuit-breaker banner, 6-session progression suggestions, and 26-week Zone 2 ramp cards).

### 3.5 Issue #17 (`DEPS`: Deferred Major Upgrades) — COMPLETE
- Executed sequentially with a clean `bun run --cwd frontend build` between every step:
  1. `tailwindcss` `3.4.19` -> `4.3.3` + `@tailwindcss/postcss@4.3.3` (migrated `postcss.config.mjs` and `globals.css` to `@import "tailwindcss";` + `@theme`).
  2. `tailwind-merge` `2.6.1` -> `3.7.0`.
  3. `lucide-react` `0.453.0` -> `1.66.0`.
  4. `typescript` `5.9.3` -> `7.0.2`.

### 3.6 Verification Gate Outputs
- **Backend (`uv run --directory backend pytest`)**: **`76 passed in 1.68s`** (CPython 3.13.14, `pytest 9.2.0`).
- **Frontend (`bun run --cwd frontend build`)**: **Exit `0`** (Next.js 16.4.3 Turbopack, TypeScript 7.0.2 in `729ms`, `3/3` static pages generated).
- **Ready for Claude Code `AUDIT_GATE`**: Mark `G05`, `G06`, and `G08` `[COMPLETED]` in `TASK_GRAPH.md` and unblock `G07` / `G09`.
