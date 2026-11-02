import sqlite3
from datetime import datetime, timedelta

import duckdb
import pytest

from engine.db import init_databases
from engine.planner import (
    CLEAN_SESSIONS_TO_PROGRESS,
    ActivityZone2,
    VitalsSample,
    baseline_zone2_minutes,
    current_plan,
    vitals_hold_reasons,
    weekly_targets,
    Exercise,
    FlareState,
    Symptom,
    SessionLog,
    SymptomReport,
    active_exercises,
    contraindication_reason,
    evaluate_symptoms,
    filter_safe,
    load_plan,
    load_session_logs,
    progression_suggestions,
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


# --- progression (suggest only) ----------------------------------------------

T0 = datetime(2026, 11, 3, 8, 0)


def logs(exercise_id: str, symptoms: list[Symptom | None]) -> list[SessionLog]:
    return [SessionLog(exercise_id, T0 + timedelta(days=i), sym) for i, sym in enumerate(symptoms)]


LUNGE = Exercise("lunge_bodyweight", "Lunge", 3, 10)


def test_threshold_is_six():
    assert CLEAN_SESSIONS_TO_PROGRESS == 6


def test_six_clean_sessions_suggests_progression_for_clinician():
    out = progression_suggestions([LUNGE], logs("lunge_bodyweight", [None] * 6))
    assert len(out) == 1
    assert out[0].exercise_id == "lunge_bodyweight"
    assert "backpack" in out[0].suggestion.lower()
    assert out[0].clean_sessions == 6
    assert "clinician" in out[0].message.lower()


def test_five_clean_sessions_is_not_enough():
    assert progression_suggestions([LUNGE], logs("lunge_bodyweight", [None] * 5)) == []


def test_symptom_resets_streak():
    seq = [None] * 6 + [Symptom.POSTERIOR_RIGHT_KNEE] + [None] * 5
    assert progression_suggestions([LUNGE], logs("lunge_bodyweight", seq)) == []


def test_streak_counts_only_after_last_symptom():
    seq = [Symptom.SHOULDER_PAIN] + [None] * 6
    out = progression_suggestions([LUNGE], logs("lunge_bodyweight", seq))
    assert out[0].clean_sessions == 6


def test_log_order_does_not_matter():
    seq = logs("lunge_bodyweight", [None] * 6)
    assert len(progression_suggestions([LUNGE], list(reversed(seq)))) == 1


def test_other_exercises_logs_are_ignored():
    assert progression_suggestions([LUNGE], logs("w_row_band", [None] * 6)) == []


def test_band_exercise_suggests_grip_change():
    row = Exercise("w_row_band", "W-row with band", 3, 10)
    out = progression_suggestions([row], logs("w_row_band", [None] * 6))
    assert "grip" in out[0].suggestion.lower()


def test_exercise_without_known_progression_is_never_suggested():
    stretch = Exercise("stretch_hamstring_left", "Hamstring stretch (left)", 2, None, 30)
    assert progression_suggestions([stretch], logs("stretch_hamstring_left", [None] * 10)) == []


def test_contraindicated_exercise_never_suggested():
    bad = Exercise("lunge_bodyweight", "Deep full squat", 3, 10)
    assert progression_suggestions([bad], logs("lunge_bodyweight", [None] * 6)) == []


def test_load_session_logs_roundtrip(tmp_path):
    _, sqlite_path = init_databases(tmp_path)
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute("INSERT INTO session_log (exercise_id, performed_at, symptom) VALUES ('lunge_bodyweight', '2026-11-03 08:00:00', NULL)")
        conn.execute("INSERT INTO session_log (exercise_id, performed_at, symptom) VALUES ('lunge_bodyweight', '2026-11-04 08:00:00', 'shoulder_pain')")
    got = load_session_logs(sqlite_path)
    assert got == [
        SessionLog("lunge_bodyweight", datetime(2026, 11, 3, 8, 0), None),
        SessionLog("lunge_bodyweight", datetime(2026, 11, 4, 8, 0), Symptom.SHOULDER_PAIN),
    ]


# --- 6-month Zone 2 periodization --------------------------------------------

AS_OF = datetime(2026, 12, 1, 12, 0)


def z2(days_ago: float, minutes: float | None) -> ActivityZone2:
    return ActivityZone2(AS_OF - timedelta(days=days_ago), None if minutes is None else minutes * 60)


def test_baseline_is_weekly_average_over_last_28_days():
    acts = [z2(1, 100), z2(10, 100), z2(20, 100), z2(27, 100)]  # 400 min / 4 weeks
    assert baseline_zone2_minutes(acts, AS_OF) == 100


def test_baseline_ignores_activities_outside_window_and_missing_zone2():
    acts = [z2(1, 120), z2(40, 999), z2(5, None)]
    assert baseline_zone2_minutes(acts, AS_OF) == 30


def test_baseline_none_without_zone2_data():
    assert baseline_zone2_minutes([z2(5, None)], AS_OF) is None
    assert baseline_zone2_minutes([], AS_OF) is None


def test_weekly_targets_ramp_ten_percent_capped_with_deload_every_fourth():
    t = weekly_targets(100.0)
    assert len(t) == 26
    assert [w.zone2_minutes for w in t[:5]] == [110.0, 121.0, 125.0, 100.0, 125.0]
    assert [w.deload for w in t[:5]] == [False, False, False, True, False]
    assert all(w.zone2_minutes <= 125.0 for w in t)
    assert all(w.strength_sessions == 3 for w in t)
    assert [w.week for w in t][:3] == [1, 2, 3]


def test_vitals_hold_freezes_first_week_only():
    t = weekly_targets(100.0, hold_reasons=("resting HR up 6 bpm",))
    assert t[0].zone2_minutes == 100.0
    assert t[0].held is True and t[0].hold_reasons == ("resting HR up 6 bpm",)
    assert t[1].zone2_minutes == 110.0
    assert t[1].held is False
    assert t[3].deload is True and t[3].zone2_minutes == 96.8


def test_weekly_targets_rejects_nonpositive_baseline():
    with pytest.raises(ValueError):
        weekly_targets(0)


def vit(days_ago: float, **kw) -> VitalsSample:
    return VitalsSample(AS_OF - timedelta(days=days_ago), **kw)


def steady(**kw):
    return [vit(d, **kw) for d in (10, 15, 20, 25, 30)]


def test_no_hold_when_vitals_stable():
    samples = steady(resting_hr=55, systolic_bp=118, peak_flow_l_min=520) + [vit(2, resting_hr=56, systolic_bp=119, peak_flow_l_min=515)]
    assert vitals_hold_reasons(samples, AS_OF) == ()


def test_hold_on_resting_hr_rise():
    samples = steady(resting_hr=55) + [vit(1, resting_hr=61), vit(3, resting_hr=61)]
    reasons = vitals_hold_reasons(samples, AS_OF)
    assert len(reasons) == 1 and "resting" in reasons[0].lower()


def test_hold_on_systolic_rise():
    samples = steady(systolic_bp=118) + [vit(2, systolic_bp=130)]
    assert any("systolic" in r.lower() for r in vitals_hold_reasons(samples, AS_OF))


def test_hold_on_peak_flow_drop():
    samples = steady(peak_flow_l_min=520) + [vit(2, peak_flow_l_min=450)]
    assert any("peak flow" in r.lower() for r in vitals_hold_reasons(samples, AS_OF))


def test_thresholds_are_inclusive_boundaries():
    # exactly +5 bpm holds; +4 does not
    assert vitals_hold_reasons(steady(resting_hr=55) + [vit(2, resting_hr=60)], AS_OF)
    assert not vitals_hold_reasons(steady(resting_hr=55) + [vit(2, resting_hr=59)], AS_OF)


def test_no_hold_without_data_in_both_windows():
    assert vitals_hold_reasons([vit(2, resting_hr=90)], AS_OF) == ()
    assert vitals_hold_reasons(steady(resting_hr=55), AS_OF) == ()


def test_current_plan_from_duckdb(tmp_path):
    duck_path, _ = init_databases(tmp_path)
    con = duckdb.connect(str(duck_path))
    for d, secs in ((1, 6000), (8, 6000), (15, 6000), (22, 6000)):
        ts = (AS_OF - timedelta(days=d)).strftime("%Y-%m-%d %H:%M:%S")
        con.execute("INSERT INTO activity_summary (activity_id, start_time, activity_type, zone2_seconds) VALUES (?, ?, 'cycling', ?)", [f"a{d}", ts, secs])
    con.close()
    plan = current_plan(duck_path, AS_OF)
    assert plan.baseline_minutes == 100.0
    assert plan.hold_reasons == ()
    assert plan.weeks[0].zone2_minutes == 110.0


def test_current_plan_none_without_activity_data(tmp_path):
    duck_path, _ = init_databases(tmp_path)
    assert current_plan(duck_path, AS_OF) is None
