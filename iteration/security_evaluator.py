import os
import re
from typing import Dict, Any, List


class SecurityEvaluator:
    """
    Simple static security scanner using deterministic blocklists.
    """

    BLOCKLIST = [
        r"\bsubprocess\b",
        r"\bos\.system\b",
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"\brequests\.",
        r"shell\s*=\s*True",
        r"OPENAI_API_KEY\s*=\s*[\"']",
        r"GITHUB_TOKEN\s*=\s*[\"']",
    ]

    FILE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".json", ".sh"}

    def validate(self, workspace_path: str) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []

        for root, _, files in os.walk(workspace_path):
            for file_name in files:
                ext = os.path.splitext(file_name)[1].lower()
                if ext not in self.FILE_EXTENSIONS:
                    continue

                full_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(full_path, workspace_path)

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    for pattern in self.BLOCKLIST:
                        if re.search(pattern, text):
                            findings.append({
                                "category": "SECURITY",
                                "message": f"Security blocklist pattern found: {pattern}",
                                "path": rel_path
                            })
                except Exception as e:
                    findings.append({
                        "category": "SECURITY",
                        "message": f"Unable to read file for security validation: {e}",
                        "path": rel_path
                    })

        return {
            "passed": len(findings) == 0,
            "findings": findings
        }
