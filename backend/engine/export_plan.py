"""Export the seeded rehab plan as JSON for the read-only Vercel page.

Run: uv run --directory backend python -m engine.export_plan
Writes frontend/src/data/rehab-plan.json (deterministic; safe to re-run).
"""
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from engine.db import init_databases
from engine.planner import contraindication_notices, load_plan

DEFAULT_OUT = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "data" / "rehab-plan.json"

STOP_RULE = (
    "Stop any exercise that aggravates your right knee (back of the knee), "
    "left glute/sciatic symptoms or shoulders, and call your clinician "
    "(Move Health) rather than waiting for the follow-up."
)


def build_plan_json() -> dict:
    # Fresh temp DB so the export always reflects the seed, never a local edit.
    with tempfile.TemporaryDirectory() as tmp:
        _, sqlite_path = init_databases(Path(tmp))
        plan = load_plan(sqlite_path)
    exercises = [
        {**{k: v for k, v in asdict(e).items()},
         "group": "stretch" if e.id.startswith("stretch_") else "strength"}
        for e in plan
    ]
    return {
        "assessed_on": "2026-11-02",
        "source": "Physio assessment 02 Nov 2026 and Move Health app list",
        "exercises": exercises,
        "contraindications": list(contraindication_notices()),
        "stop_rule": STOP_RULE,
    }


def write_plan_json(out: Path = DEFAULT_OUT) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_plan_json(), indent=2) + "\n")
    return out


if __name__ == "__main__":
    print(f"Wrote {write_plan_json()}")
