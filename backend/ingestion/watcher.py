"""Hot-folder file watcher and multi-source ingest pipeline (Node G05).

Resolves contract-to-DuckDB column mapping (`Issue #11`) without modifying
`backend/engine/db.py`, persists validated records to `biometrics.duckdb`,
and archives processed files to `data/processed/archive/`.
"""
import csv
import json
import os
import shutil
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from engine.db import PROCESSED_DIR, init_databases
from ingestion.contracts import (
    ActivitySummary,
    BloodPressureReading,
    RestingHeartRateReading,
    SpirometryReading,
)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
INGEST_DIR = ROOT_DIR / "data" / "raw" / "ingest"


# --- Explicit Contract -> DuckDB Column Mapping Layer (Issue #11) -----------

def map_blood_pressure_to_vitals_row(reading: BloodPressureReading) -> dict[str, Any]:
    """Map `BloodPressureReading` contract fields to `vitals_log` DDL columns."""
    return {
        "timestamp": reading.timestamp,
        "systolic_bp": reading.systolic,
        "diastolic_bp": reading.diastolic,
        "pulse_bpm": reading.pulse,
        "resting_hr": reading.resting_hr,
        "peak_flow_l_min": None,
        "source": reading.source or "qardio",
    }


def map_spirometry_to_vitals_row(reading: SpirometryReading) -> dict[str, Any]:
    """Map `SpirometryReading` contract fields to `vitals_log` DDL columns."""
    return {
        "timestamp": reading.timestamp,
        "systolic_bp": None,
        "diastolic_bp": None,
        "pulse_bpm": None,
        "resting_hr": None,
        "peak_flow_l_min": reading.peak_flow_l_min,
        "source": reading.source or "spirometer",
    }


def map_resting_hr_to_vitals_row(reading: RestingHeartRateReading) -> dict[str, Any]:
    """Map `RestingHeartRateReading` contract fields to `vitals_log` DDL columns."""
    return {
        "timestamp": reading.timestamp,
        "systolic_bp": None,
        "diastolic_bp": None,
        "pulse_bpm": None,
        "resting_hr": reading.resting_hr,
        "peak_flow_l_min": None,
        "source": reading.source or "garmin",
    }


def map_activity_to_db_row(activity: ActivitySummary) -> dict[str, Any]:
    """Map `ActivitySummary` contract fields to `activity_summary` DDL columns."""
    return {
        "activity_id": activity.activity_id,
        "start_time": activity.start_time,
        "activity_type": activity.activity_type,
        "duration_seconds": activity.duration_seconds,
        "avg_hr": activity.avg_heart_rate,
        "max_hr": activity.max_heart_rate,
        "zone2_seconds": activity.time_in_zone_2_seconds,
    }


# --- DuckDB Persistence Layer -----------------------------------------------

def upsert_vitals_row(con: duckdb.DuckDBPyConnection, row: dict[str, Any]) -> None:
    con.execute(
        """INSERT OR REPLACE INTO vitals_log
           (timestamp, systolic_bp, diastolic_bp, pulse_bpm, resting_hr, peak_flow_l_min, source)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            row["timestamp"],
            row["systolic_bp"],
            row["diastolic_bp"],
            row["pulse_bpm"],
            row["resting_hr"],
            row["peak_flow_l_min"],
            row["source"],
        ],
    )


def upsert_activity_row(con: duckdb.DuckDBPyConnection, row: dict[str, Any]) -> None:
    con.execute(
        """INSERT OR REPLACE INTO activity_summary
           (activity_id, start_time, activity_type, duration_seconds, avg_hr, max_hr, zone2_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            row["activity_id"],
            row["start_time"],
            row["activity_type"],
            row["duration_seconds"],
            row["avg_hr"],
            row["max_hr"],
            row["zone2_seconds"],
        ],
    )


# --- File Parsing & Routing -------------------------------------------------

def _infer_source_from_filename(file_path: Path, default: str) -> str:
    stem = file_path.stem.lower()
    for provider in ("qardio", "spirometer", "spirometry", "garmin", "polar", "apple_health"):
        if provider in stem:
            return "spirometer" if provider == "spirometry" else provider
    return default


def _parse_record_dict(raw: dict[str, Any], file_path: Path) -> tuple[str, dict[str, Any]]:
    """Classify a single record dict, validate via contract, and return (table, mapped_row)."""
    if "activity_id" in raw or "activity_type" in raw:
        normalized = dict(raw)
        if "avg_hr" in normalized and "avg_heart_rate" not in normalized:
            normalized["avg_heart_rate"] = normalized.pop("avg_hr")
        if "max_hr" in normalized and "max_heart_rate" not in normalized:
            normalized["max_heart_rate"] = normalized.pop("max_hr")
        if "zone2_seconds" in normalized and "time_in_zone_2_seconds" not in normalized:
            normalized["time_in_zone_2_seconds"] = normalized.pop("zone2_seconds")
        model = ActivitySummary.model_validate(normalized)
        return "activity_summary", map_activity_to_db_row(model)

    if "systolic" in raw or "systolic_bp" in raw:
        normalized = dict(raw)
        if "systolic_bp" in normalized and "systolic" not in normalized:
            normalized["systolic"] = normalized.pop("systolic_bp")
        if "diastolic_bp" in normalized and "diastolic" not in normalized:
            normalized["diastolic"] = normalized.pop("diastolic_bp")
        if "pulse_bpm" in normalized and "pulse" not in normalized:
            normalized["pulse"] = normalized.pop("pulse_bpm")
        normalized.setdefault("source", _infer_source_from_filename(file_path, "qardio"))
        model = BloodPressureReading.model_validate(normalized)
        return "vitals_log", map_blood_pressure_to_vitals_row(model)

    if "peak_flow_l_min" in raw:
        normalized = dict(raw)
        normalized.setdefault("source", _infer_source_from_filename(file_path, "spirometer"))
        model = SpirometryReading.model_validate(normalized)
        return "vitals_log", map_spirometry_to_vitals_row(model)

    if "resting_hr" in raw:
        normalized = dict(raw)
        normalized.setdefault("source", _infer_source_from_filename(file_path, "garmin"))
        model = RestingHeartRateReading.model_validate(normalized)
        return "vitals_log", map_resting_hr_to_vitals_row(model)

    raise ValueError(f"Unrecognized biometric record schema in {file_path.name}: {list(raw.keys())}")


def _clean_csv_row(row: dict[str, str | None]) -> dict[str, Any]:
    return {
        k.strip(): v.strip()
        for k, v in row.items()
        if k is not None and v is not None and v.strip() != ""
    }


def _load_records_from_file(file_path: Path) -> list[dict[str, Any]]:
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if "records" in payload and isinstance(payload["records"], list):
                return payload["records"]
            return [payload]
        raise ValueError(f"Unsupported JSON top-level type in {file_path.name}")

    if suffix == ".csv":
        with file_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return [_clean_csv_row(r) for r in reader if any(r.values())]

    raise ValueError(f"Unsupported ingest file extension: {file_path.suffix}")


def ingest_file(
    file_path: Path,
    processed_dir: Path = PROCESSED_DIR,
    archive: bool = True,
) -> int:
    """Validate, map, and persist all records from `file_path` into DuckDB, then archive."""
    duck_path, _ = init_databases(processed_dir)
    records = _load_records_from_file(file_path)
    mapped_items = [_parse_record_dict(rec, file_path) for rec in records]

    with closing(duckdb.connect(str(duck_path))) as con:
        for table_name, row in mapped_items:
            if table_name == "vitals_log":
                upsert_vitals_row(con, row)
            else:
                upsert_activity_row(con, row)

    if archive:
        archive_dir = processed_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        dest = archive_dir / file_path.name
        if dest.exists():
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            dest = archive_dir / f"{file_path.stem}_{stamp}{file_path.suffix}"
        shutil.move(str(file_path), str(dest))

    return len(mapped_items)


def process_ingest_directory(
    ingest_dir: Path = INGEST_DIR,
    processed_dir: Path = PROCESSED_DIR,
) -> int:
    """Process all current files in `ingest_dir` and return total ingested record count."""
    if not ingest_dir.exists():
        return 0
    total = 0
    for item in sorted(ingest_dir.iterdir()):
        if item.is_file() and not item.name.startswith("."):
            total += ingest_file(item, processed_dir=processed_dir, archive=True)
    return total


class IngestHandler(FileSystemEventHandler):
    def __init__(self, processed_dir: Path = PROCESSED_DIR) -> None:
        super().__init__()
        self.processed_dir = processed_dir

    def on_created(self, event) -> None:
        if not event.is_directory and not os.path.basename(event.src_path).startswith("."):
            src = Path(event.src_path)
            print(f"[Watcher] New incoming file: {src.name}")
            if src.exists():
                ingest_file(src, processed_dir=self.processed_dir, archive=True)


def start_watching(
    ingest_dir: Path = INGEST_DIR,
    processed_dir: Path = PROCESSED_DIR,
) -> None:
    os.makedirs(ingest_dir, exist_ok=True)
    observer = Observer()
    observer.schedule(IngestHandler(processed_dir=processed_dir), path=str(ingest_dir), recursive=False)
    observer.start()
    print(f"[Watcher] Monitoring {ingest_dir}...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    start_watching()
