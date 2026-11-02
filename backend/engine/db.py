"""Dual-store layer: DuckDB (biometric time-series) + SQLite (operational state).

Seed source: data/physio/physio-notes1.md (physio assessment, 02 Nov 2026).
Contraindicated exercises (seated knee extension, wide-grip lat pull-down) are
deliberately never seeded; the G06 planner enforces them as hard blocks.
"""
import sqlite3
from contextlib import closing
from pathlib import Path

import duckdb

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"
DUCKDB_PATH = PROCESSED_DIR / "biometrics.duckdb"
SQLITE_PATH = PROCESSED_DIR / "app_state.db"

# (id, exercise_name, sets, reps, hold_seconds, frequency_per_week, notes)
# Strength default per physio: 3 x 10, yellow band to start. Frequency not
# specified by the physio, so left NULL rather than invented.
_STRENGTH_NOTE = "Default 3x10. Stop if symptoms aggravate and call physio."
PHYSIO_SEED: list[tuple] = [
    ("squat_green_band", "Squat with band around knees", 3, 10, None, None,
     "Green band around knees, hip-width, push knees out, shallow depth. " + _STRENGTH_NOTE),
    ("lunge_bodyweight", "Lunge", 3, 10, None, None,
     "Bodyweight to start; progress with weighted backpack. " + _STRENGTH_NOTE),
    ("crab_walk_band", "Crab walk with band", 3, 10, None, None,
     "Band just above ankles, soft knees. " + _STRENGTH_NOTE),
    ("calf_raise_double_leg", "Calf raise (double-leg)", 3, 10, None, None,
     "Physio notes: start double-leg. " + _STRENGTH_NOTE),
    ("calf_raise_single_leg", "Single leg calf raise", 3, 10, None, None,
     "Listed separately in the Move Health app (screenshot 02 Nov 2026); physio notes "
     "describe it as a progression once comfortable. " + _STRENGTH_NOTE),
    ("w_row_band", "W-row with band", 3, 10, None, None,
     "Standing, palms down, floor anchor or door handle, yellow band to start. " + _STRENGTH_NOTE),
    ("internal_rotation_45", "Internal rotation at 45 degrees", 3, 10, None, None,
     "Standing, elbow at 90 degrees, turn in, yellow band to start. " + _STRENGTH_NOTE),
    ("external_rotation_band", "External rotation with band", 3, 10, None, None,
     "Standing, yellow band to start. " + _STRENGTH_NOTE),
    ("lat_pulldown_shoulder_width", "Lat pull-down (shoulder-width grip)", 3, 10, None, None,
     "Multi-gym, shoulder-width grip only; never wide grip. " + _STRENGTH_NOTE),
    ("standing_press", "Standing press (band or cable)", 3, 10, None, None,
     "Standing, yellow band to start. " + _STRENGTH_NOTE),
    ("adduction_pulldown_high_anchor", "Adduction pull-down (high anchor)", 3, 10, None, None,
     "Standing, high anchor, yellow band to start. " + _STRENGTH_NOTE),
    ("stretch_hamstring_left", "Hamstring stretch (left)", 2, None, 30, 7,
     "Hold 20-30s. Lying on back, towel around foot, knee straight. Left tighter (75-80 deg)."),
    ("stretch_hamstring_right", "Hamstring stretch (right)", 1, None, 30, 7,
     "Hold 20-30s. Lying on back, towel around foot, knee straight."),
    ("stretch_calf_achilles_right", "Calf / Achilles stretch (right)", 2, None, 30, 7,
     "PRIORITY: right calf tightness likely driving posterior right knee stiffness. "
     "ASSUMPTION: physio gave no sets/hold; 2 x 30s mirrors the other stretches. "
     "Confirm at the 2-week follow-up."),
    ("stretch_glute_figure4_left", "Glute stretch, figure-4 (left)", 2, None, 30, 7,
     "Hold 20-30s. Left glute tight; sciatica-like symptoms reported."),
    ("stretch_glute_figure4_right", "Glute stretch, figure-4 (right)", 2, None, 30, 7,
     "Hold 20-30s."),
]


def seed_physio_plans(sqlite_path: Path = SQLITE_PATH) -> None:
    """Insert baseline prescriptions. INSERT OR IGNORE: never overwrites
    plans later adjusted by the progression engine or the clinician."""
    with closing(sqlite3.connect(sqlite_path)) as conn, conn:
        conn.executemany(
            """INSERT OR IGNORE INTO physio_plans
               (id, exercise_name, prescribed_sets, prescribed_reps, hold_seconds,
                frequency_per_week, notes) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            PHYSIO_SEED,
        )


def init_databases(processed_dir: Path = PROCESSED_DIR) -> tuple[Path, Path]:
    """Create both stores (idempotent), seed the rehab baseline, return paths."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    duck_path = processed_dir / DUCKDB_PATH.name
    sqlite_path = processed_dir / SQLITE_PATH.name

    with closing(sqlite3.connect(sqlite_path)) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS physio_plans (
            id TEXT PRIMARY KEY, exercise_name TEXT NOT NULL, prescribed_sets INTEGER,
            prescribed_reps INTEGER, hold_seconds INTEGER, frequency_per_week INTEGER,
            notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS sync_tracking (
            id TEXT PRIMARY KEY, provider TEXT NOT NULL, external_id TEXT NOT NULL,
            item_type TEXT, status TEXT, synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (provider, external_id))""")
    seed_physio_plans(sqlite_path)

    with closing(duckdb.connect(str(duck_path))) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS vitals_log (
            timestamp TIMESTAMP NOT NULL, systolic_bp INTEGER, diastolic_bp INTEGER,
            pulse_bpm INTEGER, resting_hr INTEGER, peak_flow_l_min INTEGER,
            source TEXT NOT NULL, PRIMARY KEY (timestamp, source))""")
        con.execute("""CREATE TABLE IF NOT EXISTS activity_summary (
            activity_id TEXT PRIMARY KEY, start_time TIMESTAMP, activity_type TEXT,
            duration_seconds DOUBLE, avg_hr INTEGER, max_hr INTEGER, zone2_seconds DOUBLE)""")

    return duck_path, sqlite_path


if __name__ == "__main__":
    init_databases()
    print("DuckDB & SQLite initialized successfully.")
