from fastapi.testclient import TestClient
from typing import Dict, Any, Optional
import traceback


VALID_HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}


def evaluate_app(app, spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Core evaluator used by controller.
    MUST exist — controller imports this directly.
    """

    try:
        # ---------- VALIDATE APP ----------
        if not callable(app):
            return {
                "status": "failure",
                "logs": ["APP VALIDATION FAIL → app_not_callable"],
                "failing_endpoints": [],
                "schema_mismatches": []
            }

        if not spec or "endpoints" not in spec:
            return {
                "status": "failure",
                "logs": ["SPEC FAIL → no endpoints defined"],
                "failing_endpoints": [],
                "schema_mismatches": []
            }

        client = TestClient(app)

        failing = []
        logs = []

        # ---------- TEST ENDPOINTS ----------
        for ep in spec.get("endpoints", []):
            method = str(ep.get("method", "GET")).upper()
            path = str(ep.get("path", "/health"))

            if method not in VALID_HTTP_METHODS:
                failing.append({
                    "method": method,
                    "path": path,
                    "reason": "unsupported_method"
                })
                logs.append(f"{method} {path} → FAIL (unsupported method)")
                continue

            try:
                res = client.request(method, path)

                if res.status_code >= 400:
                    failing.append({
                        "method": method,
                        "path": path,
                        "reason": f"http_{res.status_code}"
                    })
                    logs.append(f"{method} {path} → FAIL ({res.status_code})")
                else:
                    logs.append(f"{method} {path} → PASS")

            except Exception as e:
                failing.append({
                    "method": method,
                    "path": path,
                    "reason": "runtime_error"
                })
                logs.append(f"{method} {path} → FAIL ({str(e)})")

        # ---------- RESULT ----------
        if failing:
            return {
                "status": "failure",
                "logs": logs,
                "failing_endpoints": failing,
                "schema_mismatches": []
            }

        return {
            "status": "success",
            "logs": logs,
            "failing_endpoints": [],
            "schema_mismatches": []
        }

    except Exception as e:
        return {
            "status": "failure",
            "logs": [
                f"CRITICAL ERROR: {str(e)}",
                traceback.format_exc()
            ],
            "failing_endpoints": [],
            "schema_mismatches": []
        }
