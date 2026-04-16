import os
import textwrap

BASE = os.getcwd()

def write_file(path: str, content: str) -> None:
    full_path = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).lstrip("\n"))
    print(f"CREATED: {path}")

write_file("iteration/convergence.py", r'''
from typing import Dict, Any


class ConvergenceController:
    """
    Deterministic termination logic for iteration loop.
    """

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations

    def should_terminate(self, iteration_no: int, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        passed = validation_result.get("passed", False)

        if passed:
            return {
                "terminate": True,
                "status": "VALIDATED_BUILD",
                "reason": "Validation passed"
            }

        if iteration_no >= self.max_iterations:
            return {
                "terminate": True,
                "status": "FAIL",
                "reason": "Maximum iterations reached"
            }

        return {
            "terminate": False,
            "status": "CONTINUE",
            "reason": "Validation failed but iteration budget remains"
        }
''')

write_file("iteration/spec_updater.py", r'''
from typing import Dict, Any, List


class SpecUpdater:
    """
    Converts validation findings into deterministic corrective constraints.
    """

    FAILURE_TO_CONSTRAINT_PREFIX = {
        "E-SYNTAX": "Fix syntax errors exactly at flagged locations.",
        "E-DEPENDENCY": "Satisfy missing or invalid dependencies without introducing new undeclared dependencies.",
        "E-STRUCTURE": "Restore required file/module/route structure.",
        "E-BEHAVIOUR": "Correct runtime behaviour to match required endpoint behaviour.",
        "E-SCHEMA": "Correct schema mismatch without weakening validation rules.",
        "E-GOVERNANCE": "Remove prohibited governance patterns and enforce deterministic output rules.",
        "E-SECURITY": "Remove or replace blocked security patterns.",
        "E-LWP": "Remove prohibited advisory/legal-outcome language and preserve non-advisory wording.",
        "E-UI": "Restore required UI artefacts and markers.",
        "E-SPEC-UNDERDETERMINED": "Do not infer; request or preserve only explicitly defined structure.",
        "E-UNKNOWN": "Correct the flagged issue conservatively without introducing new behaviour."
    }

    def derive_constraints(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        constraints = []

        for finding in findings:
            failure_code = finding.get("failure_code", "E-UNKNOWN")
            message = finding.get("message", "")
            path = finding.get("path", "")
            prefix = self.FAILURE_TO_CONSTRAINT_PREFIX.get(failure_code, self.FAILURE_TO_CONSTRAINT_PREFIX["E-UNKNOWN"])

            constraints.append({
                "failure_code": failure_code,
                "path": path,
                "constraint": f"{prefix} Path: {path}. Finding: {message}"
            })

        return constraints

    def apply_to_spec(self, spec_text: str, constraints: List[Dict[str, Any]]) -> str:
        if not constraints:
            return spec_text

        block_lines = [
            "",
            "### DETERMINISTIC CORRECTION CONSTRAINTS",
        ]

        for idx, item in enumerate(constraints, start=1):
            block_lines.append(f"{idx}. [{item['failure_code']}] {item['constraint']}")

        return spec_text.rstrip() + "\n" + "\n".join(block_lines) + "\n"
''')

write_file("iteration/run_manager.py", r'''
import json
import os
from datetime import datetime
from typing import Dict, Any


class RunManager:
    """
    Manages per-run state snapshots.
    """

    def __init__(self, runs_dir: str = "runs"):
        self.runs_dir = runs_dir
        os.makedirs(self.runs_dir, exist_ok=True)

    def _ts(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def save_iteration_state(
        self,
        run_id: str,
        iteration_no: int,
        spec_text: str,
        validation_result: Dict[str, Any],
        constraints: list
    ) -> str:
        path = os.path.join(self.runs_dir, f"{run_id}_iteration_{iteration_no}.json")
        payload = {
            "run_id": run_id,
            "iteration_no": iteration_no,
            "timestamp": self._ts(),
            "spec_text": spec_text,
            "validation_result": validation_result,
            "constraints": constraints
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return path
''')

write_file("iteration/worker.py", r'''
from typing import Dict, Any

from iteration.controller import IterationController


def execute_run(workspace_path: str, initial_spec_text: str, run_id: str = "default_run") -> Dict[str, Any]:
    controller = IterationController()
    return controller.run(
        workspace_path=workspace_path,
        initial_spec_text=initial_spec_text,
        run_id=run_id
    )
''')

write_file("iteration/controller.py", r'''
from typing import Dict, Any

from iteration.evaluator import evaluate
from iteration.convergence import ConvergenceController
from iteration.spec_updater import SpecUpdater
from iteration.run_manager import RunManager


class IterationController:
    """
    Deterministic P7 iteration loop.
    """

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.convergence = ConvergenceController(max_iterations=max_iterations)
        self.spec_updater = SpecUpdater()
        self.run_manager = RunManager()

    def run(self, workspace_path: str, initial_spec_text: str, run_id: str = "default_run") -> Dict[str, Any]:
        current_spec_text = initial_spec_text

        for iteration_no in range(1, self.max_iterations + 1):
            validation_result = evaluate(workspace_path=workspace_path, run_id=f"{run_id}_it_{iteration_no}")
            findings = validation_result.get("findings", [])
            constraints = self.spec_updater.derive_constraints(findings)

            state_path = self.run_manager.save_iteration_state(
                run_id=run_id,
                iteration_no=iteration_no,
                spec_text=current_spec_text,
                validation_result=validation_result,
                constraints=constraints
            )

            decision = self.convergence.should_terminate(
                iteration_no=iteration_no,
                validation_result=validation_result
            )

            if decision["terminate"]:
                return {
                    "run_id": run_id,
                    "iteration_no": iteration_no,
                    "status": decision["status"],
                    "reason": decision["reason"],
                    "validation_result": validation_result,
                    "constraints": constraints,
                    "state_path": state_path,
                    "updated_spec_text": current_spec_text
                }

            current_spec_text = self.spec_updater.apply_to_spec(
                spec_text=current_spec_text,
                constraints=constraints
            )

        return {
            "run_id": run_id,
            "iteration_no": self.max_iterations,
            "status": "FAIL",
            "reason": "Iteration loop exhausted",
            "validation_result": validation_result,
            "constraints": constraints,
            "state_path": state_path,
            "updated_spec_text": current_spec_text
        }
''')

print("P7 ITERATION SYSTEM WRITTEN")
