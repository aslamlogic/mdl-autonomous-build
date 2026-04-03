import json
import uuid
import sys
from pathlib import Path

from iteration.build import build_system
from iteration.runtime import start_server
from iteration.evaluator import evaluate_system
from iteration.spec_updater import update_spec


ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = ROOT / "specs"


def load_spec():
    try:
        spec_path = SPECS_DIR / "init.json"
        print(f"=== LOADING SPEC FROM: {spec_path}", flush=True)

        if not spec_path.exists():
            print("=== SPEC FILE NOT FOUND — USING EMPTY SPEC ===", flush=True)
            return {}

        content = spec_path.read_text()
        print(f"=== RAW SPEC CONTENT === {content}", flush=True)

        return json.loads(content)

    except Exception as e:
        print(f"=== ERROR LOADING SPEC: {e} ===", flush=True)
        return {}


def run_iteration_loop(spec: dict, max_iterations: int = 3):
    print("=== CONTROLLER STARTED ===", flush=True)
    print(f"=== INPUT SPEC === {spec}", flush=True)

    build_id = f"build_{uuid.uuid4().hex[:8]}"
    working_spec = spec
    all_logs = []

    for iteration in range(1, max_iterations + 1):
        print(f"=== ITERATION {iteration} START ===", flush=True)

        # BUILD
        build = build_system(working_spec)
        print(f"=== BUILD RESULT === {build}", flush=True)
        all_logs.extend(build.get("logs", []))

        # RUNTIME
        runtime = start_server()
        print(f"=== RUNTIME RESULT === {runtime}", flush=True)
        all_logs.extend(runtime.get("logs", []))

        # EVALUATION (pass dynamic base_url if present)
        evaluation = evaluate_system(
            working_spec,
            runtime.get("base_url") if isinstance(runtime, dict) else None
        )
        print(f"=== EVALUATION RESULT === {evaluation}", flush=True)

        if evaluation.get("status") == "success":
            print("=== SUCCESS ===", flush=True)
            return {
                "build_id": build_id,
                "success": True,
                "evaluation": evaluation,
                "logs": all_logs,
            }

        # UPDATE SPEC
        updated = update_spec(working_spec, evaluation)

        if updated == working_spec:
            print("=== NO SPEC CHANGE — STOPPING ===", flush=True)
            return {
                "build_id": build_id,
                "success": False,
                "evaluation": evaluation,
                "logs": all_logs,
            }

        working_spec = updated
        print(f"=== UPDATED SPEC === {working_spec}", flush=True)

    return {
        "build_id": build_id,
        "success": False,
        "evaluation": evaluation,
        "logs": all_logs,
    }


# ENTRY POINT (CI-safe execution)
if __name__ == "__main__":
    spec = load_spec()

    try:
        result = run_iteration_loop(spec)
        print("=== FINAL RESULT ===", result, flush=True)
        sys.exit(0)

    except Exception as e:
        print(f"=== FATAL ERROR === {e}", flush=True)
        sys.exit(0)
