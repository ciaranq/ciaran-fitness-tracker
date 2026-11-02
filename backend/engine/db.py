from pathlib import Path
import duckdb
import sqlite3

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"
DUCKDB_PATH = PROCESSED_DIR / "biometrics.duckdb"
SQLITE_PATH = PROCESSED_DIR / "app_state.db"

def init_databases():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS physio_plans (
            id TEXT PRIMARY KEY, exercise_name TEXT NOT NULL, prescribed_sets INTEGER,
            prescribed_reps INTEGER, hold_seconds INTEGER, frequency_per_week INTEGER,
            notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);''')
        conn.execute('''CREATE TABLE IF NOT EXISTS sync_tracking (
            id TEXT PRIMARY KEY, provider TEXT NOT NULL, external_id TEXT UNIQUE,
            item_type TEXT, status TEXT, synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);''')
        conn.commit()

    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute('''CREATE TABLE IF NOT EXISTS vitals_log (
        timestamp TIMESTAMP PRIMARY KEY, systolic_bp INTEGER, diastolic_bp INTEGER,
        pulse_bpm INTEGER, resting_hr INTEGER, peak_flow_l_min INTEGER, source TEXT);''')
    con.execute('''CREATE TABLE IF NOT EXISTS activity_summary (
        activity_id TEXT PRIMARY KEY, start_time TIMESTAMP, activity_type TEXT,
        duration_seconds DOUBLE, avg_hr INTEGER, max_hr INTEGER, zone2_seconds DOUBLE);''')
    con.close()

if __name__ == "__main__":
    init_databases()
    print("DuckDB & SQLite initialized successfully.")
