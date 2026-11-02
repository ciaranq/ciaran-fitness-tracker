import sqlite3

import pytest

from engine.db import init_databases
from engine.planner import (
    Exercise,
    FlareState,
    Symptom,
    SymptomReport,
    active_exercises,
    contraindication_reason,
    evaluate_symptoms,
    filter_safe,
    load_plan,
)


def ex(pid: str, name: str) -> Exercise:
    return Exercise(id=pid, name=name, sets=3, reps=10)


# --- contraindications -------------------------------------------------------

@pytest.mark.parametrize("name", [
    "Seated knee extension",
    "Seated Knee Extension machine",
    "Leg extension machine",
    "Wide grip lat pull-down",
    "Wide-grip lat pulldown",
    "Lat pull-down (wide grip)",
    "Deep squat",
    "Full squat with barbell",
])
def test_contraindicated_names_are_blocked(name):
    assert contraindication_reason(name) is not None


@pytest.mark.parametrize("name", [
    "Squat with band around knees",
    "Half depth squat",
    "Lat pull-down (shoulder-width grip)",
    "Lat pull down in standing",
    "Lunge",
    "Calf raise (double-leg)",
    "W-row with band",
])
def test_prescribed_names_are_allowed(name):
    assert contraindication_reason(name) is None


def test_filter_safe_splits_safe_and_blocked():
    items = [ex("a", "Lunge"), ex("b", "Seated knee extension"), ex("c", "Wide grip lat pull-down")]
    safe, blocked = filter_safe(items)
    assert [e.id for e in safe] == ["a"]
    assert {e.id for e, _ in blocked} == {"b", "c"}
    assert all(reason for _, reason in blocked)


# --- flare circuit breaker ---------------------------------------------------

def test_no_reports_is_clear():
    decision = evaluate_symptoms([])
    assert decision.state is FlareState.CLEAR
    assert decision.halted_exercise_ids == frozenset()


@pytest.mark.parametrize("symptom", list(Symptom))
def test_any_flare_symptom_triggers_stop_and_review(symptom):
    decision = evaluate_symptoms([SymptomReport(exercise_id="squat_green_band", symptom=symptom)])
    assert decision.state is FlareState.STOP_AND_REVIEW
    assert decision.halted_exercise_ids == {"squat_green_band"}
    assert decision.reasons
    assert "clinician" in decision.message.lower()


def test_multiple_reports_halt_each_exercise_once():
    decision = evaluate_symptoms([
        SymptomReport("lunge_bodyweight", Symptom.LEFT_SCIATIC_RADIATION),
        SymptomReport("lunge_bodyweight", Symptom.POSTERIOR_RIGHT_KNEE),
        SymptomReport("w_row_band", Symptom.SHOULDER_PAIN),
    ])
    assert decision.halted_exercise_ids == {"lunge_bodyweight", "w_row_band"}
    assert len(decision.reasons) == 3


def test_active_exercises_excludes_halted():
    items = [ex("lunge_bodyweight", "Lunge"), ex("w_row_band", "W-row")]
    decision = evaluate_symptoms([SymptomReport("lunge_bodyweight", Symptom.POSTERIOR_RIGHT_KNEE)])
    assert [e.id for e in active_exercises(items, decision)] == ["w_row_band"]


def test_active_exercises_unchanged_when_clear():
    items = [ex("a", "Lunge")]
    assert active_exercises(items, evaluate_symptoms([])) == items


# --- DB loader ---------------------------------------------------------------

def test_load_plan_returns_seeded_exercises(tmp_path):
    _, sqlite_path = init_databases(tmp_path)
    plan = load_plan(sqlite_path)
    assert len(plan) == 16
    assert all(contraindication_reason(e.name) is None for e in plan)


def test_load_plan_drops_contraindicated_rows_added_to_db(tmp_path):
    _, sqlite_path = init_databases(tmp_path)
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute(
            "INSERT INTO physio_plans (id, exercise_name, prescribed_sets, prescribed_reps) "
            "VALUES ('bad', 'Seated knee extension', 3, 10)"
        )
    plan = load_plan(sqlite_path)
    assert "bad" not in {e.id for e in plan}
    assert len(plan) == 16
