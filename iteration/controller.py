import traceback
import importlib.util
import sys
from pathlib import Path

from iteration.generator import generate_app
from iteration.evaluator import evaluate_system


GENERATED_APP_PATH = Path("generated_app/main.py")


def load_generated_app():
    """
    Load generated_app/main.py and return FastAPI app object.
    """
    try:
        if not GENERATED_APP_PATH.exists():
            return None, f"LOAD_ERROR: {GENERATED_APP_PATH} missing"

        module_name = "generated_app.main"

        if module_name in sys.modules:
            del sys.modules[module_name]

        spec = importlib.util.spec_from_file_location(module_name, GENERATED_APP_PATH)
        if spec is None or spec.loader is None:
            return None, "LOAD_ERROR: could not create import spec for generated_app.main"

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        if not hasattr(module, "app"):
            return None, "LOAD_ERROR: generated_app.main has no attribute 'app'"

        return module.app, None

    except Exception as e:
        return None, f"LOAD_ERROR: {str(e)}"


def update_spec(spec: dict, evaluation: dict) -> dict:
    """
    Minimal deterministic spec updater.
    """
    return spec


def run_iteration_loop(spec: dict):
    """
    Multi-iteration deterministic controller.
    """

    MAX_ITERATIONS = 3
    iterations = []

    try:
        print(f"[DEBUG SPEC] {spec}")

        current_spec = spec

        for i in range(1, MAX_ITERATIONS + 1):
            print(f"[ITERATION] Starting iteration {i}")

            # STEP 1: generate app
            generation_result = generate_app(current_spec)

            if generation_result.get("status") != "success":
                print(f"[ITERATION] Generation failed at iteration {i}")
                return {
                    "status": "failed",
                    "stage": "generation",
                    "iteration": i,
                    "error": generation_result
                }

            # STEP 2: load generated app
            app, load_error = load_generated_app()

            if load_error:
                print(f"[ITERATION] Load failed at iteration {i}: {load_error}")
                iterations.append({
                    "iteration": i,
                    "status": "failed",
                    "evaluation": {
                        "status": "failure",
                        "logs": [load_error],
                        "failing_endpoints": [],
                        "schema_mismatches": []
                    }
                })
                break

            # STEP 3: evaluate app
            evaluation = evaluate_system(app, current_spec)

            iteration_result = {
                "iteration": i,
                "status": "success" if evaluation.get("status") == "success" else "failed",
                "evaluation": evaluation
            }

            iterations.append(iteration_result)

            print(f"[ITERATION] Completed iteration {i} with status: {iteration_result['status']}")

            # TERMINATION: success
            if evaluation.get("status") == "success":
                print(f"[ITERATION] Converged at iteration {i}")
                return {
                    "status": "converged",
                    "iterations": iterations
                }

            # STEP 4: update spec
            current_spec = update_spec(current_spec, evaluation)

        # TERMINATION: max iterations reached
        print("[ITERATION] Max iterations reached")
        return {
            "status": "max_iterations_reached",
            "iterations": iterations
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }
