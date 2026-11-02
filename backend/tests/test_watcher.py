import json
from datetime import datetime

import duckdb
import pytest

from engine.db import init_databases
from engine.planner import current_plan
from ingestion.contracts import (
    ActivitySummary,
    BloodPressureReading,
    SpirometryReading,
)
from ingestion.watcher import (
    ingest_file,
    map_activity_to_db_row,
    map_blood_pressure_to_vitals_row,
    map_spirometry_to_vitals_row,
    process_ingest_directory,
)


def test_explicit_contract_to_duckdb_column_mappings():
    ts = datetime(2026, 11, 2, 8, 30)
    bp = BloodPressureReading(timestamp=ts, systolic=118, diastolic=76, pulse=58, resting_hr=56)
    bp_row = map_blood_pressure_to_vitals_row(bp)
    assert bp_row == {
        "timestamp": ts,
        "systolic_bp": 118,
        "diastolic_bp": 76,
        "pulse_bpm": 58,
        "resting_hr": 56,
        "peak_flow_l_min": None,
        "source": "qardio",
    }

    spiro = SpirometryReading(timestamp=ts, peak_flow_l_min=525)
    spiro_row = map_spirometry_to_vitals_row(spiro)
    assert spiro_row["peak_flow_l_min"] == 525
    assert spiro_row["source"] == "spirometer"

    act = ActivitySummary(
        activity_id="garmin_101",
        start_time=ts,
        activity_type="cycling",
        duration_seconds=3600.0,
        avg_heart_rate=132,
        max_heart_rate=148,
        time_in_zone_2_seconds=2700.0,
    )
    act_row = map_activity_to_db_row(act)
    assert act_row == {
        "activity_id": "garmin_101",
        "start_time": ts,
        "activity_type": "cycling",
        "duration_seconds": 3600.0,
        "avg_hr": 132,
        "max_hr": 148,
        "zone2_seconds": 2700.0,
    }


def test_watcher_roundtrip_json_and_csv_into_duckdb_and_archive(tmp_path):
    ingest_dir = tmp_path / "ingest"
    processed_dir = tmp_path / "processed"
    ingest_dir.mkdir(parents=True)
    duck_path, _ = init_databases(processed_dir)

    # 1. Qardio BP JSON
    (ingest_dir / "qardio_bp_20261102.json").write_text(
        json.dumps(
            {
                "timestamp": "2026-11-02T08:00:00",
                "systolic": 118,
                "diastolic": 76,
                "pulse": 58,
                "resting_hr": 55,
            }
        ),
        encoding="utf-8",
    )

    # 2. Spirometer Peak Flow CSV (same timestamp, different source -> composite PK works)
    (ingest_dir / "spirometry_20261102.csv").write_text(
        "timestamp,peak_flow_l_min,notes\n2026-11-02T08:00:00,530,Morning reading\n",
        encoding="utf-8",
    )

    # 3. Garmin Activity JSON batch (feeding G06 planner Zone 2 baseline)
    (ingest_dir / "garmin_activities.json").write_text(
        json.dumps(
            [
                {
                    "activity_id": "g1",
                    "start_time": "2026-11-01T07:00:00",
                    "activity_type": "cycling",
                    "duration_seconds": 3600.0,
                    "avg_heart_rate": 130,
                    "max_heart_rate": 145,
                    "time_in_zone_2_seconds": 6000.0,
                },
                {
                    "activity_id": "g2",
                    "start_time": "2026-10-25T07:00:00",
                    "activity_type": "swimming",
                    "duration_seconds": 3600.0,
                    "avg_heart_rate": 128,
                    "max_heart_rate": 142,
                    "time_in_zone_2_seconds": 6000.0,
                },
            ]
        ),
        encoding="utf-8",
    )

    count = process_ingest_directory(ingest_dir=ingest_dir, processed_dir=processed_dir)
    assert count == 4

    # Ingest folder is now empty and files are archived
    assert list(ingest_dir.iterdir()) == []
    archived = {p.name for p in (processed_dir / "archive").iterdir()}
    assert {
        "qardio_bp_20261102.json",
        "spirometry_20261102.csv",
        "garmin_activities.json",
    } <= archived

    # Verify DuckDB columns & values
    con = duckdb.connect(str(duck_path), read_only=True)
    vitals = con.execute(
        "SELECT source, systolic_bp, diastolic_bp, pulse_bpm, resting_hr, peak_flow_l_min "
        "FROM vitals_log ORDER BY source"
    ).fetchall()
    activities = con.execute(
        "SELECT activity_id, avg_hr, max_hr, zone2_seconds FROM activity_summary ORDER BY activity_id"
    ).fetchall()
    con.close()

    assert vitals == [
        ("qardio", 118, 76, 58, 55, None),
        ("spirometer", None, None, None, None, 530),
    ]
    assert activities == [
        ("g1", 130, 145, 6000.0),
        ("g2", 128, 142, 6000.0),
    ]

    # Verify G06 planner reads the ingested Zone 2 rows directly
    plan = current_plan(duck_path, as_of=datetime(2026, 11, 2, 12, 0))
    assert plan is not None
    assert plan.baseline_minutes == 50.0


def test_ingest_file_rejects_invalid_vitals_and_leaves_file_unarchived(tmp_path):
    ingest_dir = tmp_path / "ingest"
    processed_dir = tmp_path / "processed"
    ingest_dir.mkdir(parents=True)
    bad_file = ingest_dir / "qardio_bad.json"
    bad_file.write_text(
        json.dumps(
            {
                "timestamp": "2026-11-02T08:00:00",
                "systolic": 350,  # out of bounds (70..220)
                "diastolic": 76,
                "pulse": 58,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        ingest_file(bad_file, processed_dir=processed_dir)
    assert bad_file.exists()

