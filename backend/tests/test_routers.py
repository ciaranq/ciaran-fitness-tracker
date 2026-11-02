from datetime import datetime, timedelta

import duckdb
import pytest
from fastapi.testclient import TestClient

from engine.db import init_databases
from main import app
from routers.plan import get_db_paths

AS_OF = datetime(2026, 12, 1, 12, 0)


@pytest.fixture
def client_and_paths(tmp_path):
    paths = init_databases(tmp_path)
    app.dependency_overrides[get_db_paths] = lambda: paths
    with TestClient(app) as client:
        yield client, paths
    app.dependency_overrides.clear()


def test_health_endpoint(client_and_paths):
    client, _ = client_and_paths
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_get_rehab_plan_returns_16_seeded_exercises_and_contraindications(client_and_paths):
    client, _ = client_and_paths
    res = client.get("/api/v1/plan/rehab")
    assert res.status_code == 200
    body = res.json()
    assert len(body["exercises"]) == 16
    assert len(body["active_exercise_ids"]) == 16
    assert body["progression_suggestions"] == []
    assert len(body["contraindications"]) == 3
    assert body["flare_decision"]["state"] == "CLEAR"


def test_post_clean_sessions_triggers_progression_suggestion_at_six(client_and_paths):
    client, _ = client_and_paths
    t0 = datetime(2026, 11, 3, 8, 0)
    for day in range(6):
        res = client.post(
            "/api/v1/sessions",
            json={
                "exercise_id": "lunge_bodyweight",
                "performed_at": (t0 + timedelta(days=day)).isoformat(),
                "symptom": None,
            },
        )
        assert res.status_code == 201
        assert res.json()["flare_decision"]["state"] == "CLEAR"

    rehab = client.get("/api/v1/plan/rehab").json()
    suggestions = rehab["progression_suggestions"]
    assert len(suggestions) == 1
    assert suggestions[0]["exercise_id"] == "lunge_bodyweight"
    assert suggestions[0]["clean_sessions"] == 6
    assert "backpack" in suggestions[0]["suggestion"].lower()


@pytest.mark.parametrize(
    "symptom",
    ["posterior_right_knee", "left_sciatic_radiation", "shoulder_pain"],
)
def test_post_session_with_symptom_triggers_stop_and_review(client_and_paths, symptom):
    client, _ = client_and_paths
    res = client.post(
        "/api/v1/sessions",
        json={
            "exercise_id": "squat_green_band",
            "performed_at": "2026-11-05T09:00:00",
            "symptom": symptom,
        },
    )
    assert res.status_code == 201
    body = res.json()
    decision = body["flare_decision"]
    assert decision["state"] == "STOP_AND_REVIEW"
    assert decision["halted_exercise_ids"] == ["squat_green_band"]
    assert decision["reasons"]
    assert "clinician" in decision["message"].lower()

    rehab = client.get("/api/v1/plan/rehab").json()
    assert rehab["flare_decision"]["state"] == "STOP_AND_REVIEW"
    assert "squat_green_band" not in rehab["active_exercise_ids"]


def test_post_session_rejects_unknown_symptom(client_and_paths):
    client, _ = client_and_paths
    res = client.post(
        "/api/v1/sessions",
        json={"exercise_id": "squat_green_band", "symptom": "unknown_ache"},
    )
    assert res.status_code == 422


def test_periodization_returns_404_when_no_zone2_data(client_and_paths):
    client, _ = client_and_paths
    res = client.get("/api/v1/plan/periodization")
    assert res.status_code == 404


def test_periodization_returns_26_week_plan_when_zone2_data_exists(client_and_paths):
    client, (duck_path, _) = client_and_paths
    con = duckdb.connect(str(duck_path))
    for d, secs in ((1, 6000), (8, 6000), (15, 6000), (22, 6000)):
        ts = (AS_OF - timedelta(days=d)).strftime("%Y-%m-%d %H:%M:%S")
        con.execute(
            "INSERT INTO activity_summary (activity_id, start_time, activity_type, zone2_seconds) "
            "VALUES (?, ?, 'cycling', ?)",
            [f"act_{d}", ts, secs],
        )
    con.close()

    res = client.get("/api/v1/plan/periodization", params={"as_of": AS_OF.isoformat()})
    assert res.status_code == 200
    body = res.json()
    assert body["baseline_minutes"] == 100.0
    assert len(body["weeks"]) == 26
    assert body["weeks"][0]["zone2_minutes"] == 110.0


def test_baseline_summary_uses_real_duckdb_data_not_hardcoded_stub(client_and_paths):
    client, (duck_path, _) = client_and_paths
    empty = client.get("/api/v1/baseline/summary").json()
    assert empty["resting_heart_rate"] is None
    assert empty["blood_pressure"] is None
    assert empty["peak_expiratory_flow_l_min"] is None

    con = duckdb.connect(str(duck_path))
    con.execute(
        "INSERT INTO vitals_log (timestamp, systolic_bp, diastolic_bp, pulse_bpm, resting_hr, peak_flow_l_min, source) "
        "VALUES ('2026-11-02 08:00:00', 122, 78, 60, 56, 545, 'qardio')"
    )
    con.close()

    populated = client.get("/api/v1/baseline/summary").json()
    assert populated["resting_heart_rate"] == 56
    assert populated["blood_pressure"] == {"systolic": 122, "diastolic": 78}
    assert populated["peak_expiratory_flow_l_min"] == 545

