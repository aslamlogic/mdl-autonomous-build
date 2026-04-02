import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SPEC_PATH = Path("specs/init.json")


def fail(message: str) -> None:
    print(json.dumps({"status": "error", "message": message}, indent=2))
    sys.exit(1)


def read_json(path: Path) -> dict:
    if not path.exists():
        fail(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_build() -> int:
    result = subprocess.run(["python", "engine/bootstrap.py"])
    return result.returncode


def run_evaluator(base_url: str) -> dict:
    result = subprocess.run(
        ["python", "iteration/evaluator.py", base_url],
        capture_output=True,
        text=True,
    )

    if result.stdout:
        try:
            return json.loads(result.stdout)
        except Exception:
            fail("Evaluator output is not valid JSON")

    fail("Evaluator produced no output")


def get_base_url() -> str:
    url = os.getenv("DEPLOYED_URL", "").strip()
    if not url:
        fail("DEPLOYED_URL not set")
    return url.rstrip("/")


def update_spec(spec: dict, evaluation: dict) -> dict:
    # Deterministic rule-based update (minimal version)

    if evaluation["goal_satisfied"]:
        return spec

    failing = evaluation.get("failing_endpoints", [])

    endpoints = spec.get("api", {}).get("endpoints", [])

    # Simple deterministic rule:
    # If endpoint failed → ensure it exists in spec (no-op for now)
    # Future: could enrich schemas, fix types, etc.

    new_spec = spec.copy()
    new_spec["last_failure"] = failing

    return new_spec


def run_iteration(goal: str, max_iterations: int = 5) -> dict:
    spec = read_json(SPEC_PATH)
    base_url = get_base_url()

    history: list[dict[str, Any]] = []

    for i in range(max_iterations):
        print(f"\nITERATION {i + 1}")

        # Step 1 — Build
        build_code = run_build()
        if build_code != 0:
            return {
                "status": "build_failed",
                "iteration": i + 1,
            }

        # Step 2 — Evaluate
        evaluation = run_evaluator(base_url)
        history.append(evaluation)

        if evaluation.get("goal_satisfied"):
            return {
                "status": "success",
                "iterations": i + 1,
                "evaluation": evaluation,
                "history": history,
            }

        # Step 3 — Update spec
        spec = update_spec(spec, evaluation)
        write_json(SPEC_PATH, spec)

    return {
        "status": "max_iterations_reached",
        "iterations": max_iterations,
        "history": history,
    }


def main() -> None:
    goal = os.getenv("GOAL", "default_goal")
    max_iterations = int(os.getenv("MAX_ITERATIONS", "3"))

    result = run_iteration(goal, max_iterations)
    print(json.dumps(result, indent=2))

    if result["status"] == "success":
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
