import os
from typing import Dict, Any, List


class LWPValidator:
    """
    Deterministic placeholder validator for locked workflow process presence.
    This checks artefact presence and obvious prohibited language.
    """

    PROHIBITED_TERMS = ["entitled", "liable", "will win", "prediction", "guaranteed outcome"]

    def validate(self, workspace_path: str) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []

        rule_applicator = os.path.join(workspace_path, "iteration", "rule_applicator.py")
        if not os.path.exists(rule_applicator):
            findings.append({
                "category": "LWP",
                "message": "rule_applicator.py missing; deterministic LWP chain cannot be confirmed",
                "path": "iteration/rule_applicator.py"
            })

        for root, _, files in os.walk(workspace_path):
            for file_name in files:
                if not file_name.endswith((".py", ".txt", ".json", ".md")):
                    continue
                full_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(full_path, workspace_path)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        text = f.read().lower()
                    for term in self.PROHIBITED_TERMS:
                        if term in text:
                            findings.append({
                                "category": "LWP",
                                "message": f"Prohibited advisory/legal-outcome language found: {term}",
                                "path": rel_path
                            })
                except Exception:
                    pass

        return {
            "passed": len(findings) == 0,
            "findings": findings
        }
