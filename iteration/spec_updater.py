
from typing import Any, Dict, List


class SpecUpdater:
    FAILURE_TO_ACTION = {
        "E-SYNTAX": "fix_syntax",
        "E-DEPENDENCY": "fix_dependency",
        "E-STRUCTURE": "create_or_fix_structure",
        "E-BEHAVIOUR": "fix_runtime_behaviour",
        "E-SCHEMA": "fix_schema",
        "E-GOVERNANCE": "fix_governance",
        "E-SECURITY": "fix_security",
        "E-LWP": "restore_lwp_chain",
        "E-UI": "restore_ui_markers",
        "E-SPEC-UNDERDETERMINED": "stay_within_explicit_scope",
        "E-UNKNOWN": "fix_conservatively",
    }

    FAILURE_TO_GUIDANCE = {
        "E-SYNTAX": "Correct syntax without rewriting unrelated logic.",
        "E-DEPENDENCY": "Resolve imports and declarations without introducing undeclared dependencies.",
        "E-STRUCTURE": "Create missing required files or directories and populate them minimally but validly.",
        "E-BEHAVIOUR": "Implement the required endpoint or runtime behaviour exactly.",
        "E-SCHEMA": "Correct schema mismatch without weakening validation.",
        "E-GOVERNANCE": "Remove prohibited patterns and preserve deterministic execution.",
        "E-SECURITY": "Remove insecure patterns and replace them conservatively.",
        "E-LWP": "Create or repair the rule application path required for deterministic LWP validation.",
        "E-UI": "Create or repair the minimum UI markers or files required by validation.",
        "E-SPEC-UNDERDETERMINED": "Do not invent extra features beyond explicit requirements.",
        "E-UNKNOWN": "Apply the smallest safe correction to the flagged issue.",
    }

    def derive_constraints(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        repair_contract: List[Dict[str, Any]] = []

        for finding in findings:
            failure_code = str(finding.get("failure_code", "E-UNKNOWN"))
            message = str(finding.get("message", "")).strip()
            path = str(finding.get("path", "")).strip()

            repair_contract.append(
                {
                    "failure_code": failure_code,
                    "path": path,
                    "action": self.FAILURE_TO_ACTION.get(failure_code, "fix_conservatively"),
                    "guidance": self.FAILURE_TO_GUIDANCE.get(
                        failure_code,
                        self.FAILURE_TO_GUIDANCE["E-UNKNOWN"],
                    ),
                    "message": message,
                    "forbidden_regressions": [
                        "Do not modify files outside allowed_files.",
                        "Do not remove a valid /health endpoint.",
                        "Do not add markdown or commentary into source files.",
                        "Do not replace multi-file output with single-file output.",
                    ],
                }
            )

        return repair_contract
