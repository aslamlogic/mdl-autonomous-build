import traceback
import importlib.util
import sys
from pathlib import Path

from iteration.generator import generate_app
from iteration.evaluator import evaluate_system


GENERATED_APP_PATH = Path("generated_app/main.py")
MAX_ITERATIONS = 3


def load_generated_app():
    try:
        if not GENERATED_APP_PATH.exists():
            return None, f"LOAD_ERROR: {GENERATED_APP_PATH} missing"

        module_name = "generated_app.main"

        if module_name in sys.modules:
            del sys.modules[module_name]

        spec = importlib.util.spec_from_file_location(module_name, GENERATED_APP_PATH)
        if spec is None or spec.loader is None:
            return None, "LOAD_ERROR: could not create import spec"

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        if not hasattr(module, "app"):
            return None, "LOAD_ERROR: generated_app.main has no 'app'"

        return module.app, None

    except Exception as e:
        return None, f"LOAD_ERROR: {str(e)}"


def run_iteration_loop(spec: dict):
    iterations = []

    try:
        for i in range(1, MAX_ITERATIONS + 1):

            print(f"[ITERATION] Starting iteration {i}")

            # STEP 1 — generate
            gen = generate_app(spec)

            if gen.get("status") != "success":
                return {
                    "status": "failed",
                    "stage": "generation",
                    "error": gen
                }

            # STEP 2 — load
            app, load_error = load_generated_app()

            if load_error:
                evaluation = {
                    "status": "failure",
                    "logs": [load_error],
                    "failing_endpoints": [],
                    "schema_mismatches": []
                }
                iter_status = "failed"

            else:
                # STEP 3 — evaluate
                print("[DEBUG BEFORE EVAL]", spec)

                evaluation = evaluate_system(app, spec)

                iter_status = "success" if evaluation["status"] == "success" else "failed"

            iterations.append({
                "iteration": i,
                "status": iter_status,
                "evaluation": evaluation
            })

            print(f"[ITERATION] Completed iteration {i} with status: {iter_status}")

            # 🔴 CORRECT convergence logic
            if evaluation["status"] == "success":
                print(f"[ITERATION] Converged at iteration {i}")
                return {
                    "status": "converged",
                    "iterations": iterations
                }

        # 🔴 ONLY reached if ALL iterations failed
        print("[ITERATION] Max iterations reached")

        return {
            "status": "failed",
            "reason": "max_iterations_reached",
            "iterations": iterations
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }
