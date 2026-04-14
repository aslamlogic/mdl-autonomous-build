from iteration.generator import generate_code
from iteration.evaluator import evaluate_app
from iteration.spec_updater import update_spec


def run_iteration_loop(spec, max_iterations=3):
    print("🔥 NEW CONTROLLER ACTIVE 🔥")

    iterations = []
    current_spec = spec

    for i in range(1, max_iterations + 1):
        print(f"[ITERATION] Starting iteration {i}")
        print(f"[DEBUG BEFORE GENERATION] {current_spec}")

        # 1. Generate code
        generate_code(current_spec)

        # 2. Evaluate
        evaluation = evaluate_app(current_spec)

        iteration_status = "success" if evaluation["status"] == "success" else "failed"

        iterations.append({
            "iteration": i,
            "status": iteration_status,
            "evaluation": evaluation
        })

        print(f"[DEBUG AFTER EVAL] {evaluation}")

        # 3. Check convergence
        if evaluation["status"] == "success":
            print(f"[ITERATION] Converged at iteration {i}")
            return {
                "status": "converged",
                "iterations": iterations
            }

        # 4. Update spec for next iteration
        print("[SPEC UPDATE] Updating spec...")
        current_spec = update_spec(current_spec, evaluation)
        print(f"[DEBUG UPDATED SPEC] {current_spec}")

    print("[ITERATION] Max iterations reached")

    return {
        "status": "failed",
        "reason": "max_iterations_reached",
        "iterations": iterations
    }
