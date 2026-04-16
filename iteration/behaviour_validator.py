import importlib.util
import json
import os
import sys
from typing import Dict, Any, List

from fastapi.testclient import TestClient


class BehaviourValidator:
    """
    Validates runtime behaviour using FastAPI TestClient when app is present.
    """

    def _load_module_from_path(self, module_path: str):
        module_name = "_p6_runtime_target"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to create import spec for {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def validate(self, workspace_path: str) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []
        api_path = os.path.join(workspace_path, "meta_ui", "api.py")

        if not os.path.exists(api_path):
            findings.append({
                "category": "BEHAVIOUR",
                "message": "Cannot run behaviour checks because meta_ui/api.py is missing",
                "path": "meta_ui/api.py"
            })
            return {"passed": False, "findings": findings}

        try:
            module = self._load_module_from_path(api_path)
            app = getattr(module, "app", None)
            if app is None:
                findings.append({
                    "category": "BEHAVIOUR",
                    "message": "FastAPI app object 'app' not found in meta_ui/api.py",
                    "path": "meta_ui/api.py"
                })
                return {"passed": False, "findings": findings}

            client = TestClient(app)

            response = client.get("/health")
            if response.status_code != 200:
                findings.append({
                    "category": "BEHAVIOUR",
                    "message": f"/health returned status {response.status_code}, expected 200",
                    "path": "/health"
                })
            else:
                try:
                    payload = response.json()
                    if payload.get("status") != "ok":
                        findings.append({
                            "category": "BEHAVIOUR",
                            "message": f"/health payload invalid: {json.dumps(payload)}",
                            "path": "/health"
                        })
                except Exception as e:
                    findings.append({
                        "category": "BEHAVIOUR",
                        "message": f"/health returned non-JSON payload: {e}",
                        "path": "/health"
                    })

        except Exception as e:
            findings.append({
                "category": "BEHAVIOUR",
                "message": f"Runtime validation failed: {e}",
                "path": "meta_ui/api.py"
            })

        return {
            "passed": len(findings) == 0,
            "findings": findings
        }
