from typing import Any, Dict, List


class SpecUpdater:

    FILE_TEMPLATES = {
        "meta_ui/api.py": '''from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
''',

        "iteration/rule_applicator.py": '''def apply_rules(data):
    return data
''',

        "apps/__init__.py": '''# apps package'''
    }

    def derive_constraints(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        repair_contract = []

        for finding in findings:
            failure_code = finding.get("failure_code", "E-UNKNOWN")
            path = finding.get("path", "")

            action = "fix"

            if failure_code == "E-STRUCTURE":
                if path in self.FILE_TEMPLATES:
                    action = "create_file"

            if failure_code == "E-LWP":
                path = "iteration/rule_applicator.py"
                action = "create_file"

            if failure_code == "E-UI":
                path = "meta_ui/api.py"
                action = "create_file"

            repair_contract.append({
                "failure_code": failure_code,
                "action": action,
                "path": path,
                "template": self.FILE_TEMPLATES.get(path, ""),
                "message": finding.get("message", "")
            })

        return repair_contract
