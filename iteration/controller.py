import json
import uuid
from pathlib import Path

from iteration.build import build_system
from iteration.runtime import start_server
from iteration.evaluator import evaluate_system
from iteration.spec_updater import update_spec


ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = ROOT / "specs"
LOG_DIR = ROOT / "iteration"
SPECS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


def run_iteration_loop(spec: dict, max_iterations: int = 2) -> dict:
    logs: list[str] = []
    build_id = f"build_{uuid.uuid4().hex[:8]}"
    working_spec = spec

    spec_path = SPECS_DIR / "init.json"
    spec_path.write_text(json.dumps(working_spec, indent=2), encoding="utf-8")
    logs.append(f"Spec written to {spec_path}")

    deployment_url = "http://localhost:8000"

    for iteration in range(1, max_iterations + 1):
        logs.append(f"--- ITERATION {iteration} ---")

        logs.append("BUILDING SYSTEM...")
        build_result = build_system(working_spec)
        logs.extend(build_result.get("logs", []))

        logs.append("STARTING SERVER...")
        runtime_result = start_server()
        logs.extend(runtime_result.get("logs", []))

        logs.append("EVALUATING SYSTEM...")
        evaluation = evaluate_system(working_spec)
        logs.append(f"EVALUATION RESULT: {evaluation}")

        if evaluation.get("status") == "success":
            logs.append("SYSTEM SATISFIED SPECIFICATION")
            return {
                "build_id": build_id,
                "message": "Build completed successfully",
                "deployment_url": deployment_url,
                "logs": logs,
                "normalized_spec": working_spec,
            }

        logs.append("UPDATING SPEC...")
        working_spec = update_spec(working_spec, evaluation)
        spec_path.write_text(json.dumps(working_spec, indent=2), encoding="utf-8")
        logs.append("SPEC UPDATED")

    return {
        "build_id": build_id,
        "message": "Build completed but did not fully converge within iteration limit",
        "deployment_url": deployment_url,
        "logs": logs,
        "normalized_spec": working_spec,
    }
