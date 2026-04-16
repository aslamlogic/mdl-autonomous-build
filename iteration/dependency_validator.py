import importlib.util
import json
import os
from typing import Dict, Any, List


class DependencyValidator:
    """
    Checks basic Python and Node dependency presence without network installs.
    """

    def validate(self, workspace_path: str) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []

        req_txt = os.path.join(workspace_path, "requirements.txt")
        if os.path.exists(req_txt):
            with open(req_txt, "r", encoding="utf-8") as f:
                packages = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            for pkg in packages:
                module_name = pkg.split("==")[0].split(">=")[0].split("<=")[0].replace("-", "_")
                if importlib.util.find_spec(module_name) is None:
                    findings.append({
                        "category": "DEPENDENCY",
                        "message": f"Python dependency not importable: {pkg}",
                        "path": req_txt
                    })

        pkg_json = os.path.join(workspace_path, "package.json")
        if os.path.exists(pkg_json):
            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                deps = {}
                deps.update(data.get("dependencies", {}))
                deps.update(data.get("devDependencies", {}))
                node_modules = os.path.join(workspace_path, "node_modules")
                if not os.path.isdir(node_modules):
                    findings.append({
                        "category": "DEPENDENCY",
                        "message": "package.json exists but node_modules directory is missing",
                        "path": pkg_json
                    })
                else:
                    for dep in deps.keys():
                        dep_path = os.path.join(node_modules, dep)
                        if not os.path.exists(dep_path):
                            findings.append({
                                "category": "DEPENDENCY",
                                "message": f"Node dependency missing from node_modules: {dep}",
                                "path": pkg_json
                            })
            except Exception as e:
                findings.append({
                    "category": "DEPENDENCY",
                    "message": f"package.json parse failure: {e}",
                    "path": pkg_json
                })

        return {
            "passed": len(findings) == 0,
            "findings": findings
        }
