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
