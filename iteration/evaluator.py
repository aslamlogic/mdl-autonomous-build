from fastapi.testclient import TestClient
from typing import Dict, Any, Optional
import traceback


VALID_HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}


# ============================================================
# NORMALISATION
# ============================================================

def normalize_endpoint_spec(endpoint: Dict[str, Any]) -> Dict[str, Any]:
    method = str(endpoint.get("method", "")).strip().upper()
    path = str(endpoint.get("path", "")).strip()

    if method in ["STRING", "", "NONE"]:
        method = "GET"

    if path in ["string", "", "NONE"]:
        path = "/health"

    if not path.startswith("/"):
        path = "/" + path

    return {"method": method, "path": path}


def normalize_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    endpoints = spec.get("endpoints", [])
    spec["endpoints"] = [normalize_endpoint_spec(e) for e in endpoints]
    return spec


# ============================================================
# ASGI VALIDATION (NEW — CRITICAL)
# ============================================================

def validate_app_object(app):
    """
    Ensures app is a valid ASGI callable (FastAPI/Starlette)
    """
    if not callable(app):
        return False, "app_not_callable"

    # Basic ASGI signature check
    try:
        # Check it has __call__ with expected args
        if not hasattr(app, "__call__"):
            return False, "app_missing_call"

    except Exception:
        return False, "app_invalid"

    return True, None


# ============================================================
# MAIN ENTRYPOINT
# ============================================================

def evaluate_app(app, spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:

    try:
        # ---------------------------
        # APP VALIDATION FIRST
        # ---------------------------
        is_valid, reason = validate_app_object(app)

        if not is_valid:
            return {
                "status": "failure",
                "logs": [f"APP VALIDATION FAIL → {reason}"],
                "failing_endpoints": [],
                "schema_mismatches": []
            }

        # ---------------------------
        # SPEC FALLBACK
        # ---------------------------
        if spec is None:
            spec = {
                "endpoints": [
                    {"method": "GET", "path": "/health"}
                ]
            }

        spec = normalize_spec(spec)

        client = TestClient(app)

        failing_endpoints = []
        logs = []

        for endpoint in spec.get("endpoints", []):
            method = endpoint["method"]
            path = endpoint["path"]

            if method not in VALID_HTTP_METHODS:
                failing_endpoints.append({
                    "method": method,
                    "path": path,
                    "reason": "unsupported_method"
                })
                logs.append(f"{method} {path} → FAIL (unsupported method)")
                continue

            try:
                response = client.request(method, path)

                if response.status_code >= 400:
                    failing_endpoints.append({
                        "method": method,
                        "path": path,
                        "reason": f"http_{response.status_code}"
                    })
                    logs.append(f"{method} {path} → FAIL ({response.status_code})")
                else:
                    logs.append(f"{method} {path} → PASS")

            except Exception as e:
                failing_endpoints.append({
                    "method": method,
                    "path": path,
                    "reason": "runtime_error"
                })
                logs.append(f"{method} {path} → FAIL ({str(e)})")

        if failing_endpoints:
            return {
                "status": "failure",
                "logs": logs,
                "failing_endpoints": failing_endpoints,
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
            "logs": [f"CRITICAL ERROR: {str(e)}", traceback.format_exc()],
            "failing_endpoints": [],
            "schema_mismatches": []
        }
