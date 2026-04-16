import ast
import os
from typing import Dict, Any, List

from iteration.behaviour_validator import BehaviourValidator
from iteration.dependency_validator import DependencyValidator
from iteration.failure_classifier import FailureClassifier
from iteration.governance_validator import GovernanceValidator
from iteration.lwp_validator import LWPValidator
from iteration.report_builder import ReportBuilder
from iteration.security_evaluator import SecurityEvaluator
from iteration.structure_validator import StructureValidator
from iteration.ui_evaluator import UIEvaluator


class Evaluator:
    """
    Hardened P6 orchestrator.
    """

    def __init__(self):
        self.dependency_validator = DependencyValidator()
        self.structure_validator = StructureValidator()
        self.behaviour_validator = BehaviourValidator()
        self.governance_validator = GovernanceValidator()
        self.security_validator = SecurityEvaluator()
        self.lwp_validator = LWPValidator()
        self.ui_validator = UIEvaluator()
        self.failure_classifier = FailureClassifier()
        self.report_builder = ReportBuilder()

    def _syntax_validate_python(self, workspace_path: str) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []
        for root, _, files in os.walk(workspace_path):
            for file_name in files:
                if file_name.endswith(".py"):
                    full_path = os.path.join(root, file_name)
                    rel_path = os.path.relpath(full_path, workspace_path)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            source = f.read()
                        ast.parse(source)
                    except SyntaxError as e:
                        findings.append({
                            "category": "SYNTAX",
                            "message": f"Python syntax error: {e}",
                            "path": rel_path
                        })
                    except Exception as e:
                        findings.append({
                            "category": "SYNTAX",
                            "message": f"Python parse failure: {e}",
                            "path": rel_path
                        })
        return {
            "passed": len(findings) == 0,
            "findings": findings
        }

    def run(self, workspace_path: str, run_id: str = "default_run") -> Dict[str, Any]:
        results = []

        syntax_result = self._syntax_validate_python(workspace_path)
        results.append(syntax_result)

        dependency_result = self.dependency_validator.validate(workspace_path)
        results.append(dependency_result)

        structure_result = self.structure_validator.validate(workspace_path)
        results.append(structure_result)

        behaviour_result = self.behaviour_validator.validate(workspace_path)
        results.append(behaviour_result)

        governance_result = self.governance_validator.validate(workspace_path)
        results.append(governance_result)

        security_result = self.security_validator.validate(workspace_path)
        results.append(security_result)

        lwp_result = self.lwp_validator.validate(workspace_path)
        results.append(lwp_result)

        ui_result = self.ui_validator.validate(workspace_path)
        results.append(ui_result)

        all_findings: List[Dict[str, Any]] = []
        for result in results:
            all_findings.extend(result.get("findings", []))

        classified_findings = self.failure_classifier.classify(all_findings)
        passed = len(classified_findings) == 0

        report_path = self.report_builder.build_validation_report(
            run_id=run_id,
            passed=passed,
            findings=classified_findings
        )

        return {
            "passed": passed,
            "findings": classified_findings,
            "report_path": report_path
        }


def evaluate(workspace_path: str, run_id: str = "default_run") -> Dict[str, Any]:
    return Evaluator().run(workspace_path=workspace_path, run_id=run_id)
