import sqlite3

import duckdb
import pytest

from engine.db import init_databases, seed_physio_plans

FORBIDDEN = ("seated knee extension", "wide grip", "wide-grip")


@pytest.fixture
def paths(tmp_path):
    return init_databases(tmp_path)


def _plans(sqlite_path):
    with sqlite3.connect(sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        return {r["id"]: dict(r) for r in conn.execute("SELECT * FROM physio_plans")}


def test_init_creates_both_databases_and_tables(paths):
    duck_path, sqlite_path = paths
    assert duck_path.exists() and sqlite_path.exists()

    con = duckdb.connect(str(duck_path))
    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    con.close()
    assert {"vitals_log", "activity_summary"} <= tables

    with sqlite3.connect(sqlite_path) as conn:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"physio_plans", "sync_tracking"} <= names


def test_init_is_idempotent(tmp_path):
    init_databases(tmp_path)
    _, sqlite_path = init_databases(tmp_path)
    first = _plans(sqlite_path)
    init_databases(tmp_path)
    assert _plans(sqlite_path) == first


def test_seed_matches_physio_notes(paths):
    plans = _plans(paths[1])
    assert len(plans) == 16  # 11 strength + 5 stretch rows
    assert plans["calf_raise_single_leg"]["prescribed_sets"] == 3

    squat = plans["squat_green_band"]
    assert (squat["prescribed_sets"], squat["prescribed_reps"]) == (3, 10)
    assert "green" in squat["notes"].lower()

    assert plans["stretch_hamstring_left"]["prescribed_sets"] == 2
    assert plans["stretch_hamstring_right"]["prescribed_sets"] == 1
    assert plans["stretch_glute_figure4_left"]["prescribed_sets"] == 2
    assert plans["stretch_glute_figure4_right"]["prescribed_sets"] == 2
    assert "priority" in plans["stretch_calf_achilles_right"]["notes"].lower()
    for pid, row in plans.items():
        if pid.startswith("stretch_"):
            assert row["hold_seconds"] == 30
            assert row["frequency_per_week"] == 7


def test_seed_never_contains_contraindicated_exercises(paths):
    for row in _plans(paths[1]).values():
        name = row["exercise_name"].lower()
        assert not any(bad in name for bad in FORBIDDEN)
    lat = _plans(paths[1])["lat_pulldown_shoulder_width"]
    assert "shoulder-width" in lat["notes"].lower()


def test_seed_does_not_overwrite_edited_plan(paths):
    _, sqlite_path = paths
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute("UPDATE physio_plans SET prescribed_sets = 4 WHERE id = 'squat_green_band'")
    seed_physio_plans(sqlite_path)
    assert _plans(sqlite_path)["squat_green_band"]["prescribed_sets"] == 4


def test_sync_tracking_unique_per_provider(paths):
    _, sqlite_path = paths
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute("INSERT INTO sync_tracking (id, provider, external_id) VALUES ('a', 'google_tasks', 'x1')")
        conn.execute("INSERT INTO sync_tracking (id, provider, external_id) VALUES ('b', 'google_calendar', 'x1')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO sync_tracking (id, provider, external_id) VALUES ('c', 'google_tasks', 'x1')")



def test_vitals_log_allows_same_timestamp_different_source(paths):
    con = duckdb.connect(str(paths[0]))
    con.execute("INSERT INTO vitals_log (timestamp, systolic_bp, source) VALUES ('2026-11-02 08:00:00', 118, 'qardio')")
    con.execute("INSERT INTO vitals_log (timestamp, peak_flow_l_min, source) VALUES ('2026-11-02 08:00:00', 520, 'spirometer')")
    with pytest.raises(duckdb.ConstraintException):
        con.execute("INSERT INTO vitals_log (timestamp, systolic_bp, source) VALUES ('2026-11-02 08:00:00', 120, 'qardio')")
    con.close()
