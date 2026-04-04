import json
import uuid
import sys
from pathlib import Path

from iteration.build import build_system
from iteration.evaluator import evaluate_system
from iteration.spec_updater import update_spec

ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = ROOT / "specs"


def load_spec():
    try:
        p = SPECS_DIR / "init.json"
        if not p.exists():
            return {}
        return json.loads(p.read_text())
    except Exception:
        return {}


def run_iteration_loop(spec: dict, max_iterations: int = 3):
    build_id = f"build_{uuid.uuid4().hex[:8]}"
    working_spec = spec
    logs = []

    for _ in range(max_iterations):
        build = build_system(working_spec)
        logs.extend(build.get("logs", []))

        evaluation = evaluate_system(working_spec)

        if evaluation.get("status") == "success":
            return {
                "build_id": build_id,
                "success": True,
                "evaluation": evaluation,
                "logs": logs,
            }

        updated = update_spec(working_spec, evaluation)
        if updated == working_spec:
            return {
                "build_id": build_id,
                "success": False,
                "evaluation": evaluation,
                "logs": logs,
            }

        working_spec = updated

    return {
        "build_id": build_id,
        "success": False,
        "evaluation": evaluation,
        "logs": logs,
    }


if __name__ == "__main__":
    try:
        result = run_iteration_loop(load_spec())
        print(result)
        sys.exit(0)
    except Exception:
        sys.exit(0)
