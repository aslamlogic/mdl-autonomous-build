import os
import re
from typing import Dict, Any, List


class GovernanceValidator:
    """
    Enforces no-markdown, no narrative contamination, deterministic textual restrictions.
    """

    PROHIBITED_PATTERNS = [
        r"```",
        r"\bAs we can see\b",
        r"\bIn this section\b",
        r"\bNext, we\b",
        r"\bHere is an explanation\b",
    ]

    ALLOWED_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".json", ".yaml", ".yml", ".txt", ".md", ".toml", ".ini", ".cfg", ".sh"
    }

    def validate(self, workspace_path: str) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []

        for root, _, files in os.walk(workspace_path):
            for file_name in files:
                ext = os.path.splitext(file_name)[1].lower()
                if ext not in self.ALLOWED_EXTENSIONS:
                    continue

                full_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(full_path, workspace_path)

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    for pattern in self.PROHIBITED_PATTERNS:
                        if re.search(pattern, text):
                            findings.append({
                                "category": "GOVERNANCE",
                                "message": f"Prohibited governance pattern found: {pattern}",
                                "path": rel_path
                            })
                except Exception as e:
                    findings.append({
                        "category": "GOVERNANCE",
                        "message": f"Unable to read file for governance validation: {e}",
                        "path": rel_path
                    })

        return {
            "passed": len(findings) == 0,
            "findings": findings
        }
