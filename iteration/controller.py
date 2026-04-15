"""
iteration/controller.py

Controller with external run_id support
"""

from pathlib import Path
import json
import uuid
from datetime import datetime, timezone

from iteration.deploy import deploy_system
from iteration.evaluator import evaluate_app
from iteration.file_writer import write_files
from iteration.spec_updater import update_spec_with_failures

from iteration.run_registry import (
    create_run,
    update_iteration,
    mark_completed,
    mark_failed
)

from engine.llm_interface import generate_code


MAX_ITERATIONS = 3


# ============================================================
# MAIN LOOP
# ============================================================

def run_iteration_loop(spec: dict, project_id: str = "default", run_id: str = None):

    if not run_id:
        run_id = generate_run_id()

    create_run(run_id, project_id, MAX_ITERATIONS)

    run_dir = Path(f"runs/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=True)

    current_spec = spec

    for i in range(1, MAX_ITERATIONS + 1):

        update_iteration(run_id, i)

        iteration_dir = run_dir / f"iteration_{i}"
        iteration_dir.mkdir(parents=True, exist_ok=True)

        write_json(iteration_dir / "spec_before.json", current_spec)

        # GENERATE
        gen = generate_code(json.dumps(current_spec, indent=2))
        write_json(iteration_dir / "generation.json", gen)

        if not gen.get("success"):
            mark_failed(run_id, gen.get("error_message", "generation failed"))
            return

        # WRITE
        write = write_files(gen)
        write_json(iteration_dir / "write.json", write)

        if not write.get("success"):
            mark_failed(run_id, write.get("error_message", "write failed"))
            return

        # VALIDATE
        val = evaluate_app(current_spec)
        write_json(iteration_dir / "validation.json", val)

        if not val.get("overall_pass"):
            current_spec = update_spec_with_failures(current_spec, val)
            write_json(iteration_dir / "spec_after.json", current_spec)
            continue

        # DEPLOY
        dep = deploy_system(validation_report=val)
        write_json(iteration_dir / "deployment.json", dep)

        if not dep.get("success"):
            mark_failed(run_id, dep.get("error_message", "deployment failed"))
            return

        # SUCCESS
        mark_completed(run_id, dep.get("live_url"))
        return

    mark_failed(run_id, "max iterations reached")


# ============================================================
# UTIL
# ============================================================

def generate_run_id():
    return f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:6]}"


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
