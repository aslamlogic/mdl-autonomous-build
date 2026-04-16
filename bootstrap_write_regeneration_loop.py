import os
import textwrap

BASE = os.getcwd()

def write_file(path: str, content: str) -> None:
    full_path = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).lstrip("\n"))
    print(f"CREATED: {path}")

write_file("iteration/controller.py", r'''
from __future__ import annotations

import json
import os
from typing import Dict, Any, List

from iteration.evaluator import evaluate
from iteration.convergence import ConvergenceController
from iteration.spec_updater import SpecUpdater
from iteration.run_manager import RunManager
from iteration.logging_service import LoggingService


class IterationController:
    """
    Deterministic P7 loop with regeneration integrated.

    Flow:
    spec -> prompt -> generate -> write -> validate -> derive constraints -> repeat
    """

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.convergence = ConvergenceController(max_iterations=max_iterations)
        self.spec_updater = SpecUpdater()
        self.run_manager = RunManager()
        self.logger = LoggingService()

    def _load_prompt_builder(self):
        from iteration.prompt_builder import PromptBuilder
        return PromptBuilder()

    def _load_generator(self):
        from engine.llm_interface import generate
        return generate

    def _workspace_target_path(self, workspace_path: str) -> str:
        target = os.path.join(workspace_path, "apps", "generated_app", "main.py")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        return target

    def _write_generated_output(self, generated_output: str, workspace_path: str) -> str:
        """
        Writes generated output using engine.file_writer if available.
        Falls back to deterministic direct write.
        """
        target_path = self._workspace_target_path(workspace_path)

        try:
            from engine.file_writer import write_output
            try:
                write_output(generated_output, target_path)
                return target_path
            except TypeError:
                write_output(generated_output)
                return target_path
        except Exception:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(generated_output)
            return target_path

    def _generate_candidate(self, spec_text: str) -> Dict[str, Any]:
        builder = self._load_prompt_builder()
        prompt = builder.build({"raw": spec_text, "length": len(spec_text)})

        generator = self._load_generator()
        generated_output = generator(prompt)

        return {
            "prompt": prompt,
            "generated_output": generated_output
        }

    def run(self, workspace_path: str, initial_spec_text: str, run_id: str = "default_run") -> Dict[str, Any]:
        current_spec_text = initial_spec_text
        last_validation_result: Dict[str, Any] = {}
        last_constraints: List[Dict[str, Any]] = []
        last_state_path = ""

        for iteration_no in range(1, self.max_iterations + 1):
            self.logger.log(run_id, "iteration_start", "running", {"iteration_no": iteration_no})

            generation_result = self._generate_candidate(current_spec_text)
            self.logger.log(
                run_id,
                "generation_complete",
                "ok",
                {
                    "iteration_no": iteration_no,
                    "generated_length": len(generation_result["generated_output"])
                }
            )

            written_target = self._write_generated_output(
                generated_output=generation_result["generated_output"],
                workspace_path=workspace_path
            )
            self.logger.log(
                run_id,
                "file_write_complete",
                "ok",
                {
                    "iteration_no": iteration_no,
                    "target_path": written_target
                }
            )

            validation_result = evaluate(
                workspace_path=workspace_path,
                run_id=f"{run_id}_it_{iteration_no}"
            )
            findings = validation_result.get("findings", [])
            constraints = self.spec_updater.derive_constraints(findings)

            state_path = self.run_manager.save_iteration_state(
                run_id=run_id,
                iteration_no=iteration_no,
                spec_text=current_spec_text,
                validation_result=validation_result,
                constraints=constraints
            )

            self.logger.log(
                run_id,
                "validation_complete",
                "ok" if validation_result.get("passed", False) else "failed",
                {
                    "iteration_no": iteration_no,
                    "finding_count": len(findings),
                    "state_path": state_path
                }
            )

            decision = self.convergence.should_terminate(
                iteration_no=iteration_no,
                validation_result=validation_result
            )

            last_validation_result = validation_result
            last_constraints = constraints
            last_state_path = state_path

            if decision["terminate"]:
                final_payload = {
                    "run_id": run_id,
                    "iteration_no": iteration_no,
                    "status": decision["status"],
                    "reason": decision["reason"],
                    "validation_result": validation_result,
                    "constraints": constraints,
                    "state_path": state_path,
                    "updated_spec_text": current_spec_text,
                    "target_path": written_target
                }
                self.logger.log(run_id, "iteration_terminate", decision["status"], final_payload)
                return final_payload

            current_spec_text = self.spec_updater.apply_to_spec(
                spec_text=current_spec_text,
                constraints=constraints
            )

            self.logger.log(
                run_id,
                "spec_updated",
                "ok",
                {
                    "iteration_no": iteration_no,
                    "constraint_count": len(constraints)
                }
            )

        fallback_payload = {
            "run_id": run_id,
            "iteration_no": self.max_iterations,
            "status": "FAIL",
            "reason": "Iteration loop exhausted",
            "validation_result": last_validation_result,
            "constraints": last_constraints,
            "state_path": last_state_path,
            "updated_spec_text": current_spec_text
        }
        self.logger.log(run_id, "iteration_exhausted", "FAIL", fallback_payload)
        return fallback_payload
''')

write_file("iteration/worker.py", r'''
from __future__ import annotations

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

print("REGENERATION LOOP INTEGRATION WRITTEN")
