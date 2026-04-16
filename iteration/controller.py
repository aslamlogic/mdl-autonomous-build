
import os
from typing import Any, Dict, List, Set

from engine.llm_interface import generate
from iteration.evaluator import evaluate
from iteration.spec_updater import SpecUpdater


class IterationController:
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.spec_updater = SpecUpdater()

    def _allowed_files(self) -> List[str]:
        return [
            "generated_app/main.py",
            "meta_ui/api.py",
            "iteration/controller.py",
            "iteration/rule_applicator.py",
            "apps/__init__.py",
        ]

    def _full_path(self, workspace_path: str, relative_path: str) -> str:
        return os.path.join(workspace_path, relative_path)

    def _write_files(self, workspace_path: str, files: Dict[str, str]) -> None:
        for relative_path, content in files.items():
            full_path = self._full_path(workspace_path, relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

    def _score(self, result: Dict[str, Any]) -> int:
        findings = result.get("findings", []) or []
        passed = bool(result.get("passed", False))
        return (10 if passed else 0) - len(findings)

    def _failure_signature(self, result: Dict[str, Any]) -> Set[str]:
        findings = result.get("findings", []) or []
        signature: Set[str] = set()
        for finding in findings:
            code = str(finding.get("failure_code", "E-UNKNOWN"))
            path = str(finding.get("path", ""))
            message = str(finding.get("message", ""))
            signature.add(f"{code}|{path}|{message}")
        return signature

    def run(self, workspace_path: str, initial_spec_text: str, run_id: str = "run") -> Dict[str, Any]:
        previous_score = None
        previous_signature: Set[str] = set()
        repair_contract: List[Dict[str, Any]] = []
        allowed_files = self._allowed_files()

        for iteration_index in range(self.max_iterations):
            print(f"ITERATION {iteration_index}")

            generated_files = generate(
                spec_text=initial_spec_text,
                repair_contract=repair_contract,
                allowed_files=allowed_files,
            )

            self._write_files(workspace_path, generated_files)

            main_path = self._full_path(workspace_path, "generated_app/main.py")
            main_content = ""
            if os.path.exists(main_path):
                with open(main_path, "r", encoding="utf-8") as f:
                    main_content = f.read()

            result = evaluate(main_content)
            score = self._score(result)
            print(f"Score: {score}")

            if result.get("passed", False):
                print("VALIDATED_BUILD")
                return {
                    "status": "SUCCESS",
                    "score": score,
                    "iteration": iteration_index,
                    "result": result,
                }

            current_signature = self._failure_signature(result)

            if previous_score is not None and score <= previous_score:
                print("NO IMPROVEMENT -> STOP")
                return {
                    "status": "FAIL",
                    "reason": "no_improvement",
                    "score": score,
                    "iteration": iteration_index,
                    "result": result,
                }

            if previous_signature and current_signature == previous_signature:
                print("IDENTICAL FAILURE SIGNATURE -> STOP")
                return {
                    "status": "FAIL",
                    "reason": "identical_failure_signature",
                    "score": score,
                    "iteration": iteration_index,
                    "result": result,
                }

            repair_contract = self.spec_updater.derive_constraints(result.get("findings", []) or [])
            previous_score = score
            previous_signature = current_signature

        return {
            "status": "FAIL",
            "reason": "max_iterations_reached",
            "iteration": self.max_iterations,
        }
