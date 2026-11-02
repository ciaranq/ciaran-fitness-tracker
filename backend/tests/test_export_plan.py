import json

from engine.export_plan import build_plan_json, write_plan_json


def test_plan_json_contains_seeded_exercises_grouped():
    plan = build_plan_json()
    assert plan["assessed_on"] == "2026-11-02"
    assert len(plan["exercises"]) == 16
    groups = {e["group"] for e in plan["exercises"]}
    assert groups == {"strength", "stretch"}
    assert sum(e["group"] == "stretch" for e in plan["exercises"]) == 5
    squat = next(e for e in plan["exercises"] if e["id"] == "squat_green_band")
    assert (squat["sets"], squat["reps"]) == (3, 10)


def test_plan_json_lists_contraindications_and_stop_rule():
    plan = build_plan_json()
    text = " ".join(plan["contraindications"]).lower()
    assert "knee extension" in text and "wide-grip" in text
    assert "stop" in plan["stop_rule"].lower()
    assert not any("knee extension" in e["name"].lower() for e in plan["exercises"])


def test_write_plan_json_is_deterministic(tmp_path):
    out = tmp_path / "plan.json"
    write_plan_json(out)
    first = out.read_text()
    write_plan_json(out)
    assert out.read_text() == first
    assert json.loads(first) == build_plan_json()
