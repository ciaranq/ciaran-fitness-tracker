# REQUIREMENTS.md: Ciaran Fitness Tracker

## 1. Overview & Objectives
Cardio-pulmonary health, biometric telemetry, and adaptive physiotherapy engine aggregating:
- **Garmin Connect & Polar HR Strap**: Activity `.fit`/JSON summaries, resting HR, and Zone 2 aerobic time-in-zone.
- **QardioArm Blood Pressure**: Systolic, diastolic, and pulse time-series.
- **Spirometer Peak Flow**: Expiratory peak flow (`L/min`) tracking.
- **Apple Health**: Daily step counts and supplemental vitals.
- **Clinical Physiotherapy (`data/physio/physio-notes1.md`)**: Structured strength and stretching protocols synced to Move Health, Google Tasks, and Google Calendar.

**Primary 6-Month Goal**: Build a safe, injury-free general strength foundation alongside Zone 2 aerobic base conditioning to return to freestyle swimming and bushwalking (correcting historical over-index on cardio vs. strength).

---

## 2. Stack & Tooling Non-Negotiables
- **Frontend**: Next.js (App Router), TypeScript 5.x, Tailwind CSS, Lucide icons, glassmorphic dark UI (`#080c14`). Runtime & package manager: **`bun` only** (never `npm`, `yarn`, or `pnpm`).
- **Backend**: Python 3.12+, FastAPI, Pydantic v2, Polars, Watchdog, Garth/GarminConnect, Fitparse. Package manager: **`uv` only** (`uv run`, `uv add`, `pytest`, `ruff`; never raw `pip` or `conda`).
- **Dual-Store Architecture (`data/processed/`)**:
  - **Analytical (`biometrics.duckdb`)**: High-density biometric time-series (`vitals_log`, `activity_summary`).
  - **Operational (`app_state.db` SQLite)**: Rehabilitation prescriptions (`physio_plans`) and external sync state (`sync_tracking`).
- **Hot-Folder Ingest**: `data/raw/ingest/` monitored by `backend/ingestion/watcher.py`, archiving processed files to `data/processed/archive/`.

---

## 3. Clinical Rehabilitation & Safety Constraints (`data/physio/physio-notes1.md` — 02 Nov 2026)

### 3.1 Baseline Assessment & Asymmetries
- **Shoulders**: Prior bilateral rotator cuff issues (resolved via ultrasound-guided injection); mild residual stiffness, no acute pain.
- **Right Lower Chain**: Tight right gastrocnemius/calf (sensitive medial belly) driving posterior right knee morning stiffness; prior right meniscus history (ligament/ACL/meniscus stress tests clear).
- **Left Lower Chain**: Tight left glute and left hamstring (`75-80°` vs. right `80-85°`), random-onset sciatica-like symptoms from glute base to knee (including at rest).

### 3.2 Prescribed Exercise Program (Default: 3 sets x 10 reps, Yellow Band start)
- **Legs & Glutes**:
  - Squats with **green resistance band** around knees (hip-width, push knees out, shallow depth).
  - Lunges (bodyweight to start; progress via weighted backpack).
  - Crab walk with band just above ankles, soft knees.
  - Calf raises (start double-leg; progress to single-leg when comfortable).
- **Shoulders & Arms (Standing Priority to engage legs/core)**:
  - W-row with band (floor anchor or door handle), palms down.
  - Internal rotation at 45° (elbow at 90°, turn in).
  - External rotation with band.
  - Lat pull-down on multi-gym, **shoulder-width grip only**.
  - Standing press with band or cable.
  - Adduction pull-down with high anchor.

### 3.3 Daily Stretching Protocol (Asymmetric)
- **Left Hamstring**: `2 reps x 20–30s` (supine, towel around foot, knee straight).
- **Right Hamstring**: `1 rep x 20–30s`.
- **Right Calf / Achilles**: **High priority** given clinical tightness driving right knee stiffness.
- **Glutes (Figure-4)**: `2 reps each side x 20–30s`.

### 3.4 Hard Contraindications & Circuit Breakers
- **NEVER prescribe**: Seated knee extension machine; wide-grip lat pull-downs; deep knee flexion under heavy load.
- **Symptom Flare Circuit Breaker**: Any exercise that aggravates posterior right knee pain, left sciatic radiation, or shoulder pain must immediately halt (`STOP_AND_REVIEW`) and prompt clinician contact ahead of the 2-week follow-up.

---

## 4. GitHub Issue Tracker (`ciaranq/ciaran-fitness-tracker`)
- **Issue #1 (CLOSED)**: `[G01-G03] [COMPLETED]` Workspace Hardening, Ingest Contracts & Frontend Skeleton
- **Issue #2 (OPEN)**: `[G04] [Claude]` DuckDB & SQLite Dual-Store Layer & Clinical Rehab Seeding
- **Issue #3 (OPEN)**: `[G05] [AGY]` File Watcher Hot-Folder Loop & Multi-Source Ingest Pipeline
- **Issue #4 (OPEN)**: `[G06] [Claude]` Periodization, Rehab Progression & Recovery Engine
- **Issue #5 (OPEN)**: `[G07] [AGY]` Google Workspace Bi-Directional Sync (Tasks & Calendar)
- **Issue #6 (OPEN)**: `[G08-G09] [AGY + Claude]` Glassmorphic Biometric HUD & E2E Canary Release
