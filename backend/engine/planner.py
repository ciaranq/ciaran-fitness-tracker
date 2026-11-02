"""Rehab planner: clinical safety core (G06 step 1).

Pure functions over plain dataclasses; `load_plan` is the only DB access.
Rules come from the physio assessment of 02 Nov 2026
(data/physio/physio-notes1.md, REQUIREMENTS.md section 3.4).
"""
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from engine.db import SQLITE_PATH


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


# --- DB loader ---------------------------------------------------------------

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
