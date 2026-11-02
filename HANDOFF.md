# HANDOFF.md: Current Agent Execution Context

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
- Step 2: rehab progression (3x10, yellow band, double -> single-leg). Step 3: 6-month Zone 2 periodization gated by vitals. Then router ticket for AGY.
