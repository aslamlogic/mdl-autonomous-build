import os
from typing import Dict, Any, List


class StructureValidator:
    """
    Validates required files and directory presence.
    """

    REQUIRED_ANY = [
        "meta_ui/api.py",
        "iteration/controller.py",
    ]

    def validate(self, workspace_path: str) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []

        for rel_path in self.REQUIRED_ANY:
            full = os.path.join(workspace_path, rel_path)
            if not os.path.exists(full):
                findings.append({
                    "category": "STRUCTURE",
                    "message": f"Required file missing: {rel_path}",
                    "path": rel_path
                })

        apps_dir = os.path.join(workspace_path, "apps")
        if not os.path.isdir(apps_dir):
            findings.append({
                "category": "STRUCTURE",
                "message": "apps/ directory missing",
                "path": "apps/"
            })

        return {
            "passed": len(findings) == 0,
            "findings": findings
        }
