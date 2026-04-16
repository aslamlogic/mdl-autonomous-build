import os
from typing import Dict, Any, List


class UIEvaluator:
    """
    Validates presence of required UI artefacts statically.
    """

    REQUIRED_UI_FILES = [
        "meta_ui/api.py"
    ]

    OPTIONAL_UI_MARKERS = [
        "spec_upload",
        "dashboard",
        "fault_panel",
        "deploy_panel"
    ]

    def validate(self, workspace_path: str) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []

        for rel_path in self.REQUIRED_UI_FILES:
            full_path = os.path.join(workspace_path, rel_path)
            if not os.path.exists(full_path):
                findings.append({
                    "category": "UI",
                    "message": f"Required UI-related file missing: {rel_path}",
                    "path": rel_path
                })

        found_markers = set()
        for root, _, files in os.walk(workspace_path):
            for file_name in files:
                if file_name.endswith((".py", ".tsx", ".ts", ".js")):
                    full_path = os.path.join(root, file_name)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            text = f.read().lower()
                        for marker in self.OPTIONAL_UI_MARKERS:
                            if marker in text:
                                found_markers.add(marker)
                    except Exception:
                        pass

        if len(found_markers) == 0:
            findings.append({
                "category": "UI",
                "message": "No expected UI markers found in codebase",
                "path": "workspace"
            })

        return {
            "passed": len(findings) == 0,
            "findings": findings
        }
