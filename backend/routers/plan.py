"""FastAPI router for the G06 rehab & periodization planner and real vitals summary.

Calls pure functions in `engine.planner` and storage helpers in `engine.db`
without reimplementing clinical rules.
"""
import sqlite3
from contextlib import closing
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import duckdb
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from engine.db import PROCESSED_DIR, init_databases
from engine.planner import (
    FlareDecision,
    FlareState,
    Symptom,
    SymptomReport,
    active_exercises,
    contraindication_notices,
    current_plan,
    evaluate_symptoms,
    load_plan,
    load_session_logs,
    progression_suggestions,
)

router = APIRouter(prefix="/api/v1", tags=["planner"])


def get_db_paths() -> tuple[Path, Path]:
    """Initialize (idempotently) and return (duck_path, sqlite_path)."""
    return init_databases(PROCESSED_DIR)


class FlareDecisionOut(BaseModel):
    state: FlareState
    halted_exercise_ids: list[str]
    reasons: list[str]
    message: str


class ExerciseOut(BaseModel):
    id: str
    name: str
    sets: int | None
    reps: int | None
    hold_seconds: int | None
    notes: str | None
    group: str


class ProgressionSuggestionOut(BaseModel):
    exercise_id: str
    suggestion: str
    clean_sessions: int
    message: str


class RehabPlanResponse(BaseModel):
    exercises: list[ExerciseOut]
    active_exercise_ids: list[str]
    progression_suggestions: list[ProgressionSuggestionOut]
    contraindications: list[str]
    flare_decision: FlareDecisionOut


class SessionCreateRequest(BaseModel):
    exercise_id: str = Field(..., min_length=1)
    performed_at: datetime | None = None
    symptom: Symptom | None = None


class SessionCreateResponse(BaseModel):
    id: int
    exercise_id: str
    performed_at: datetime
    symptom: Symptom | None
    flare_decision: FlareDecisionOut


class WeeklyTargetOut(BaseModel):
    week: int
    zone2_minutes: float
    strength_sessions: int
    deload: bool
    held: bool
    hold_reasons: list[str]


class PeriodizationPlanResponse(BaseModel):
    baseline_minutes: float
    hold_reasons: list[str]
    weeks: list[WeeklyTargetOut]


class BloodPressureSummary(BaseModel):
    systolic: int | None
    diastolic: int | None


class BaselineSummaryResponse(BaseModel):
    resting_heart_rate: int | None
    blood_pressure: BloodPressureSummary | None
    peak_expiratory_flow_l_min: int | None
    baseline_zone2_minutes: float | None
    phase: str


def _serialize_flare(decision: FlareDecision) -> FlareDecisionOut:
    return FlareDecisionOut(
        state=decision.state,
        halted_exercise_ids=sorted(decision.halted_exercise_ids),
        reasons=list(decision.reasons),
        message=decision.message,
    )


@router.get("/plan/rehab", response_model=RehabPlanResponse)
def get_rehab_plan(paths: tuple[Path, Path] = Depends(get_db_paths)) -> RehabPlanResponse:
    _, sqlite_path = paths
    plan = load_plan(sqlite_path)
    logs = load_session_logs(sqlite_path)
    suggestions = progression_suggestions(plan, logs)

    # Check latest logged session per exercise for active unresolved flare
    latest_by_exercise: dict[str, Symptom | None] = {}
    for log in sorted(logs, key=lambda item: item.performed_at):
        latest_by_exercise[log.exercise_id] = log.symptom

    active_reports = [
        SymptomReport(exercise_id=ex_id, symptom=sym)
        for ex_id, sym in latest_by_exercise.items()
        if sym is not None
    ]
    flare = evaluate_symptoms(active_reports)
    permitted = active_exercises(plan, flare)

    exercises_out = [
        ExerciseOut(
            id=ex.id,
            name=ex.name,
            sets=ex.sets,
            reps=ex.reps,
            hold_seconds=ex.hold_seconds,
            notes=ex.notes,
            group="stretch" if ex.id.startswith("stretch_") else "strength",
        )
        for ex in plan
    ]
    suggestions_out = [ProgressionSuggestionOut(**asdict(s)) for s in suggestions]

    return RehabPlanResponse(
        exercises=exercises_out,
        active_exercise_ids=[ex.id for ex in permitted],
        progression_suggestions=suggestions_out,
        contraindications=list(contraindication_notices()),
        flare_decision=_serialize_flare(flare),
    )


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
def create_session_log(
    payload: SessionCreateRequest,
    paths: tuple[Path, Path] = Depends(get_db_paths),
) -> SessionCreateResponse:
    _, sqlite_path = paths
    ts = payload.performed_at or datetime.now()
    symptom_val = payload.symptom.value if payload.symptom is not None else None

    with closing(sqlite3.connect(sqlite_path)) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO session_log (exercise_id, performed_at, symptom) VALUES (?, ?, ?)",
            (payload.exercise_id, ts.isoformat(sep=" "), symptom_val),
        )
        row_id = int(cursor.lastrowid or 0)

    reports = (
        [SymptomReport(exercise_id=payload.exercise_id, symptom=payload.symptom)]
        if payload.symptom is not None
        else []
    )
    decision = evaluate_symptoms(reports)

    return SessionCreateResponse(
        id=row_id,
        exercise_id=payload.exercise_id,
        performed_at=ts,
        symptom=payload.symptom,
        flare_decision=_serialize_flare(decision),
    )


@router.get("/plan/periodization", response_model=PeriodizationPlanResponse)
def get_periodization_plan(
    as_of: datetime | None = None,
    paths: tuple[Path, Path] = Depends(get_db_paths),
) -> PeriodizationPlanResponse:
    duck_path, _ = paths
    plan = current_plan(duck_path, as_of=as_of)
    if plan is None:
        raise HTTPException(
            status_code=404,
            detail="No Zone 2 baseline data available.",
        )
    return PeriodizationPlanResponse(
        baseline_minutes=plan.baseline_minutes,
        hold_reasons=list(plan.hold_reasons),
        weeks=[
            WeeklyTargetOut(
                week=w.week,
                zone2_minutes=w.zone2_minutes,
                strength_sessions=w.strength_sessions,
                deload=w.deload,
                held=w.held,
                hold_reasons=list(w.hold_reasons),
            )
            for w in plan.weeks
        ],
    )


@router.get("/baseline/summary", response_model=BaselineSummaryResponse)
def get_baseline_summary(
    as_of: datetime | None = None,
    paths: tuple[Path, Path] = Depends(get_db_paths),
) -> BaselineSummaryResponse:
    duck_path, _ = paths
    with closing(duckdb.connect(str(duck_path), read_only=True)) as con:
        rhr_row = con.execute(
            "SELECT resting_hr FROM vitals_log WHERE resting_hr IS NOT NULL ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        bp_row = con.execute(
            "SELECT systolic_bp, diastolic_bp FROM vitals_log "
            "WHERE systolic_bp IS NOT NULL AND diastolic_bp IS NOT NULL "
            "ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        pef_row = con.execute(
            "SELECT peak_flow_l_min FROM vitals_log WHERE peak_flow_l_min IS NOT NULL ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()

    plan = current_plan(duck_path, as_of=as_of)
    return BaselineSummaryResponse(
        resting_heart_rate=int(rhr_row[0]) if rhr_row else None,
        blood_pressure=(
            BloodPressureSummary(systolic=int(bp_row[0]), diastolic=int(bp_row[1]))
            if bp_row
            else None
        ),
        peak_expiratory_flow_l_min=int(pef_row[0]) if pef_row else None,
        baseline_zone2_minutes=plan.baseline_minutes if plan else None,
        phase="Base Conditioning (Month 1)" if plan else "Awaiting Baseline Telemetry",
    )

