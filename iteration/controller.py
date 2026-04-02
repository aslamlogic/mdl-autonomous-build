import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from copy import deepcopy
import json

from engine.bootstrap import build_system
from iteration.evaluator import evaluate_system
from iteration.spec_updater import update_spec
from iteration.fault_log import log_faults
from iteration.git_commit import commit_and_push


SPEC_PATH = "specs/init.json"
MAX_ITERATIONS = 5
BASE_URL = "http://localhost:8000"


def _load_spec() -> dict:
    if not os.path.exists(SPEC_PATH):
        return {}
    with open(SPEC_PATH, "r") as f:
        return json.load(f)


def _save_spec(spec: dict) -> None:
    with open(SPEC_PATH, "w") as f:
        json.dump(spec, f, indent=2)


def run_controller() -> dict:
    spec = _load_spec()

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n--- ITERATION {iteration} ---")

        # 1. Build
        build_system(spec)

        # 2. Evaluate
        evaluation = evaluate_system(spec, BASE_URL)
        print("EVALUATION RESULT:", evaluation)

        # 3. Log faults
        log_faults(spec, evaluation)

        # 4. Success check
        if evaluation.get("status") == "success":
            print("SUCCESS — stopping loop")

            # ---- COMMIT GENERATED SYSTEM ----
            commit_and_push()

            return {
                "status": "success",
                "iterations": iteration,
                "goal_satisfied": True,
            }

        # 5. Update spec
        print("UPDATING SPEC...")
        new_spec = update_spec(spec, evaluation)

        # 6. Detect no-op
        if new_spec == spec:
            print("NO CHANGE IN SPEC — stopping to avoid infinite loop")
            return {
                "status": "stalled",
                "iterations": iteration,
                "goal_satisfied": False,
            }

        spec = deepcopy(new_spec)
        _save_spec(spec)

    print("MAX ITERATIONS REACHED — stopping")
    return {
        "status": "failed",
        "iterations": MAX_ITERATIONS,
        "goal_satisfied": False,
    }


if __name__ == "__main__":
    run_controller()
