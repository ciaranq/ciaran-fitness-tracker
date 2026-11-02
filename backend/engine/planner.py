"""Rehab planner: clinical safety core (G06 step 1).

Pure functions over plain dataclasses; `load_plan` is the only DB access.
Rules come from the physio assessment of 02 Nov 2026
(data/physio/physio-notes1.md, REQUIREMENTS.md section 3.4).
"""
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import duckdb

from engine.db import DUCKDB_PATH, SQLITE_PATH


@dataclass(frozen=True)
class Exercise:
    id: str
    name: str
    sets: int | None
    reps: int | None
    hold_seconds: int | None = None
    notes: str | None = None


# --- contraindications (hard blocks) ----------------------------------------
# Matched against the exercise NAME only. Notes may legitimately say
# "never wide grip", so scanning them would block the safe variant.

_CONTRAINDICATIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"knee[\s-]+extension|leg[\s-]+extension", re.I),
     "Seated knee extension machine is contraindicated (physio, 02 Nov 2026)."),
    (re.compile(r"(?=.*pull[\s-]*down)(?=.*\bwide\b)", re.I),
     "Wide-grip lat pull-down is contraindicated; shoulder-width grip only."),
    (re.compile(r"(?=.*\bsquat)(?=.*\b(deep|full)\b)", re.I),
     "Deep knee flexion under load is contraindicated; keep squats shallow."),
)


def contraindication_reason(exercise_name: str) -> str | None:
    """Return why an exercise is blocked, or None if it is allowed."""
    for pattern, reason in _CONTRAINDICATIONS:
        if pattern.search(exercise_name):
            return reason
    return None


def filter_safe(
    exercises: list[Exercise],
) -> tuple[list[Exercise], list[tuple[Exercise, str]]]:
    """Split into (safe, [(blocked, reason), ...]). Order preserved."""
    safe: list[Exercise] = []
    blocked: list[tuple[Exercise, str]] = []
    for e in exercises:
        reason = contraindication_reason(e.name)
        if reason:
            blocked.append((e, reason))
        else:
            safe.append(e)
    return safe, blocked


# --- symptom flare circuit breaker ------------------------------------------

class Symptom(str, Enum):
    POSTERIOR_RIGHT_KNEE = "posterior_right_knee"
    LEFT_SCIATIC_RADIATION = "left_sciatic_radiation"
    SHOULDER_PAIN = "shoulder_pain"


class FlareState(str, Enum):
    CLEAR = "CLEAR"
    STOP_AND_REVIEW = "STOP_AND_REVIEW"


@dataclass(frozen=True)
class SymptomReport:
    exercise_id: str
    symptom: Symptom


@dataclass(frozen=True)
class FlareDecision:
    state: FlareState
    halted_exercise_ids: frozenset[str]
    reasons: tuple[str, ...]
    message: str


_SYMPTOM_LABEL = {
    Symptom.POSTERIOR_RIGHT_KNEE: "posterior right knee pain/stiffness",
    Symptom.LEFT_SCIATIC_RADIATION: "left glute/sciatic radiation",
    Symptom.SHOULDER_PAIN: "shoulder pain",
}


def evaluate_symptoms(reports: list[SymptomReport]) -> FlareDecision:
    """Any reported flare symptom halts that exercise and escalates to the clinician."""
    if not reports:
        return FlareDecision(FlareState.CLEAR, frozenset(), (), "")
    reasons = tuple(f"{r.exercise_id}: {_SYMPTOM_LABEL[r.symptom]}" for r in reports)
    return FlareDecision(
        state=FlareState.STOP_AND_REVIEW,
        halted_exercise_ids=frozenset(r.exercise_id for r in reports),
        reasons=reasons,
        message=(
            "Stop the listed exercise(s). Contact your clinician (Move Health) now "
            "rather than waiting for the 2-week follow-up."
        ),
    )


def active_exercises(exercises: list[Exercise], decision: FlareDecision) -> list[Exercise]:
    """Exercises still permitted after a flare decision."""
    return [e for e in exercises if e.id not in decision.halted_exercise_ids]


# --- progression (suggest only; the clinician confirms) ----------------------

# Physio gave no number for "when comfortable". Default pending the 2-week follow-up.
CLEAN_SESSIONS_TO_PROGRESS = 6

_BAND_GRIP = "Shift your grip on the band to increase resistance."
_PROGRESSIONS: dict[str, str] = {
    "lunge_bodyweight": "Add a weighted backpack.",
    "crab_walk_band": _BAND_GRIP,
    "w_row_band": _BAND_GRIP,
    "internal_rotation_45": _BAND_GRIP,
    "external_rotation_band": _BAND_GRIP,
    "standing_press": _BAND_GRIP,
    "adduction_pulldown_high_anchor": _BAND_GRIP,
}


@dataclass(frozen=True)
class SessionLog:
    exercise_id: str
    performed_at: datetime
    symptom: Symptom | None = None


@dataclass(frozen=True)
class ProgressionSuggestion:
    exercise_id: str
    suggestion: str
    clean_sessions: int
    message: str


def _clean_streak(exercise_id: str, logs: list[SessionLog]) -> int:
    """Consecutive symptom-free sessions, newest first, until a symptom."""
    streak = 0
    for log in sorted((l for l in logs if l.exercise_id == exercise_id),
                      key=lambda l: l.performed_at, reverse=True):
        if log.symptom is not None:
            break
        streak += 1
    return streak


def progression_suggestions(
    exercises: list[Exercise], logs: list[SessionLog]
) -> list[ProgressionSuggestion]:
    """Flag exercises eligible to progress. Never edits the plan: clinician decides."""
    out: list[ProgressionSuggestion] = []
    safe, _ = filter_safe(exercises)
    for e in safe:
        step = _PROGRESSIONS.get(e.id)
        if step is None:
            continue
        streak = _clean_streak(e.id, logs)
        if streak >= CLEAN_SESSIONS_TO_PROGRESS:
            out.append(ProgressionSuggestion(
                exercise_id=e.id,
                suggestion=step,
                clean_sessions=streak,
                message=f"{e.name}: {streak} symptom-free sessions. {step} "
                        "Confirm with your clinician before changing the prescription.",
            ))
    return out


# --- DB loaders --------------------------------------------------------------

def load_session_logs(sqlite_path: Path = SQLITE_PATH) -> list[SessionLog]:
    with closing(sqlite3.connect(sqlite_path)) as conn:
        rows = conn.execute(
            "SELECT exercise_id, performed_at, symptom FROM session_log ORDER BY performed_at, id"
        ).fetchall()
    return [
        SessionLog(r[0], datetime.fromisoformat(r[1]), Symptom(r[2]) if r[2] else None)
        for r in rows
    ]


def load_plan(sqlite_path: Path = SQLITE_PATH) -> list[Exercise]:
    """Load physio_plans and drop any contraindicated row (defence in depth)."""
    with closing(sqlite3.connect(sqlite_path)) as conn:
        rows = conn.execute(
            "SELECT id, exercise_name, prescribed_sets, prescribed_reps, hold_seconds, notes "
            "FROM physio_plans ORDER BY rowid"
        ).fetchall()
    plan = [Exercise(id=r[0], name=r[1], sets=r[2], reps=r[3], hold_seconds=r[4], notes=r[5]) for r in rows]
    safe, _ = filter_safe(plan)
    return safe


# --- 6-month Zone 2 periodization --------------------------------------------
# Every number below is an ASSUMPTION (physio gave no cardio targets), agreed
# with the user on 02 Nov 2026 and pending clinician confirmation.

PLAN_WEEKS = 26
STRENGTH_SESSIONS_PER_WEEK = 3
WEEKLY_RAMP = 0.10
ZONE2_CAP_MULTIPLIER = 1.25
DELOAD_EVERY_N_WEEKS = 4
DELOAD_FACTOR = 0.8
BASELINE_DAYS = 28
VITALS_RECENT_DAYS = 7
VITALS_BASELINE_DAYS = 28  # the 28 days before the recent window
HOLD_RESTING_HR_RISE_BPM = 5
HOLD_SYSTOLIC_RISE_MMHG = 10
HOLD_PEAK_FLOW_DROP_FRACTION = 0.10


@dataclass(frozen=True)
class ActivityZone2:
    start_time: datetime
    zone2_seconds: float | None


@dataclass(frozen=True)
class VitalsSample:
    timestamp: datetime
    resting_hr: int | None = None
    systolic_bp: int | None = None
    peak_flow_l_min: int | None = None


@dataclass(frozen=True)
class WeeklyTarget:
    week: int
    zone2_minutes: float
    strength_sessions: int
    deload: bool
    held: bool
    hold_reasons: tuple[str, ...]


@dataclass(frozen=True)
class PeriodizationPlan:
    baseline_minutes: float
    hold_reasons: tuple[str, ...]
    weeks: list[WeeklyTarget]


def baseline_zone2_minutes(activities: list[ActivityZone2], as_of: datetime) -> float | None:
    """Average weekly Zone 2 minutes over the last 28 days; None if no Zone 2 data."""
    start = as_of - timedelta(days=BASELINE_DAYS)
    secs = [a.zone2_seconds for a in activities
            if a.zone2_seconds is not None and start < a.start_time <= as_of]
    if not secs:
        return None
    return sum(secs) / 60 / (BASELINE_DAYS / 7)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def vitals_hold_reasons(samples: list[VitalsSample], as_of: datetime) -> tuple[str, ...]:
    """Reasons to hold the weekly increase: last 7 days drifted from the prior 28.

    Missing data in either window never triggers a hold. This reports drift
    only; it is not medical advice.
    """
    recent_start = as_of - timedelta(days=VITALS_RECENT_DAYS)
    prior_start = recent_start - timedelta(days=VITALS_BASELINE_DAYS)
    recent = [s for s in samples if recent_start < s.timestamp <= as_of]
    prior = [s for s in samples if prior_start < s.timestamp <= recent_start]

    def means(attr: str) -> tuple[float | None, float | None]:
        return (
            _mean([getattr(s, attr) for s in recent if getattr(s, attr) is not None]),
            _mean([getattr(s, attr) for s in prior if getattr(s, attr) is not None]),
        )

    reasons: list[str] = []
    r, p = means("resting_hr")
    if r is not None and p is not None and r - p >= HOLD_RESTING_HR_RISE_BPM:
        reasons.append(f"Resting HR up {r - p:.0f} bpm vs prior 28-day average.")
    r, p = means("systolic_bp")
    if r is not None and p is not None and r - p >= HOLD_SYSTOLIC_RISE_MMHG:
        reasons.append(f"Systolic BP up {r - p:.0f} mmHg vs prior 28-day average.")
    r, p = means("peak_flow_l_min")
    if r is not None and p is not None and p > 0 and (p - r) / p >= HOLD_PEAK_FLOW_DROP_FRACTION:
        reasons.append(f"Peak flow down {(p - r) / p:.0%} vs prior 28-day average.")
    return tuple(reasons)


def weekly_targets(
    baseline_minutes: float,
    hold_reasons: tuple[str, ...] = (),
    weeks: int = PLAN_WEEKS,
) -> list[WeeklyTarget]:
    """Zone 2 ramps 10%/week to a cap of 1.25x baseline; every 4th week deloads.

    Vitals holds freeze week 1 at baseline; the ramp resumes after.
    """
    if baseline_minutes <= 0:
        raise ValueError("baseline_minutes must be > 0")
    cap = baseline_minutes * ZONE2_CAP_MULTIPLIER
    build = baseline_minutes
    out: list[WeeklyTarget] = []
    for n in range(1, weeks + 1):
        held = n == 1 and bool(hold_reasons)
        deload = n % DELOAD_EVERY_N_WEEKS == 0
        if deload:
            minutes = build * DELOAD_FACTOR
        else:
            if not held:
                build = min(build * (1 + WEEKLY_RAMP), cap)
            minutes = build
        out.append(WeeklyTarget(
            week=n,
            zone2_minutes=round(minutes, 1),
            strength_sessions=STRENGTH_SESSIONS_PER_WEEK,
            deload=deload,
            held=held,
            hold_reasons=hold_reasons if held else (),
        ))
    return out


def load_zone2_activities(duck_path: Path = DUCKDB_PATH) -> list[ActivityZone2]:
    with closing(duckdb.connect(str(duck_path), read_only=True)) as con:
        rows = con.execute("SELECT start_time, zone2_seconds FROM activity_summary").fetchall()
    return [ActivityZone2(r[0], r[1]) for r in rows]


def load_vitals(duck_path: Path = DUCKDB_PATH) -> list[VitalsSample]:
    with closing(duckdb.connect(str(duck_path), read_only=True)) as con:
        rows = con.execute(
            "SELECT timestamp, resting_hr, systolic_bp, peak_flow_l_min FROM vitals_log"
        ).fetchall()
    return [VitalsSample(*r) for r in rows]


def current_plan(duck_path: Path = DUCKDB_PATH, as_of: datetime | None = None) -> PeriodizationPlan | None:
    """26-week plan from the user's own data; None when there is no Zone 2 baseline."""
    as_of = as_of or datetime.now()
    baseline = baseline_zone2_minutes(load_zone2_activities(duck_path), as_of)
    if baseline is None or baseline <= 0:
        return None
    reasons = vitals_hold_reasons(load_vitals(duck_path), as_of)
    return PeriodizationPlan(baseline, reasons, weekly_targets(baseline, reasons))
