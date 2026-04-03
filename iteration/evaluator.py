import json
from typing import Any, Dict, List

import requests

from iteration.schema_validator import validate_json_schema


BASE_URL = "http://localhost:8000"


def evaluate_system(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates running system against spec.
    MUST return structure compatible with controller + spec_updater.
    """

    logs: List[str] = []
    failing_endpoints: List[str] = []
    schema_mismatches: List[Dict[str, Any]] = []

    endpoints = spec.get("endpoints", [])

    if not endpoints:
        logs.append("No endpoints defined in spec")
        return {
            "status": "failure",
            "logs": logs,
            "failing_endpoints": [],
            "schema_mismatches": [{"issue": "no_endpoints"}],
        }

    for ep in endpoints:
        method = ep.get("method", "GET").upper()
        path = ep.get("path")
        expected = ep.get("expected_response", {})

        if not path:
            schema_mismatches.append({"issue": "invalid_endpoint_spec", "endpoint": ep})
            continue

        url = f"{BASE_URL}{path}"
        logs.append(f"Calling {method} {url}")

        try:
            response = _call(method, url)
        except Exception as e:
            logs.append(f"Request failed: {str(e)}")
            failing_endpoints.append(f"{method} {path}")
            schema_mismatches.append({
                "method": method,
                "path": path,
                "issue": "request_failed",
                "details": str(e),
            })
            continue

        if response.status_code >= 400:
            logs.append(f"HTTP error: {response.status_code}")
            failing_endpoints.append(f"{method} {path}")
            schema_mismatches.append({
                "method": method,
                "path": path,
                "issue": "http_error",
                "status_code": response.status_code,
                "body": safe_text(response),
            })
            continue

        try:
            data = response.json()
        except json.JSONDecodeError:
            logs.append("Invalid JSON response")
            failing_endpoints.append(f"{method} {path}")
            schema_mismatches.append({
                "method": method,
                "path": path,
                "issue": "invalid_json",
                "body": safe_text(response),
            })
            continue

        mismatches = validate_json_schema(expected, data)
        if mismatches:
            logs.append(f"Schema mismatch: {mismatches}")
            failing_endpoints.append(f"{method} {path}")
            schema_mismatches.append({
                "method": method,
                "path": path,
                "expected": expected,
                "actual": data,
                "mismatches": mismatches,
            })

    success = len(failing_endpoints) == 0 and len(schema_mismatches) == 0

    logs.append("Evaluation success" if success else "Evaluation failed")

    return {
        "status": "success" if success else "failure",
        "logs": logs,
        "failing_endpoints": failing_endpoints,
        "schema_mismatches": schema_mismatches,
    }


def _call(method: str, url: str) -> requests.Response:
    if method == "GET":
        return requests.get(url, timeout=5)
    if method == "POST":
        return requests.post(url, timeout=5)
    if method == "PUT":
        return requests.put(url, timeout=5)
    if method == "DELETE":
        return requests.delete(url, timeout=5)

    raise ValueError(f"Unsupported method: {method}")


def safe_text(response: requests.Response) -> str:
    try:
        return response.text[:500]
    except Exception:
        return "<unreadable>"
