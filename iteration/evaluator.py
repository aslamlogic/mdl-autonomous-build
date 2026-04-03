import json
from typing import Any, Dict, List

import requests

from iteration.schema_validator import validate_json_schema


DEFAULT_BASE_URL = "http://localhost:8000"


def evaluate_system(spec: Dict[str, Any], base_url: str = DEFAULT_BASE_URL) -> Dict[str, Any]:
    """
    Evaluates the generated application by calling expected endpoints
    and validating response schemas.

    Expected spec structure:
    {
        "endpoints": [
            {
                "method": "GET",
                "path": "/health",
                "expected_response": {
                    "status": "string"
                }
            }
        ]
    }
    """

    checked_endpoints = 0
    failing_endpoints: List[str] = []
    schema_mismatches: List[Dict[str, Any]] = []

    endpoints = spec.get("endpoints", [])

    if not endpoints:
        return {
            "status": "failure",
            "goal_satisfied": False,
            "base_url": base_url,
            "checked_endpoints": 0,
            "failing_endpoints": [],
            "schema_mismatches": [
                {
                    "issue": "no_endpoints_in_spec"
                }
            ],
        }

    for endpoint in endpoints:
        method = endpoint.get("method", "GET").upper()
        path = endpoint.get("path")
        expected_response = endpoint.get("expected_response", {})

        if not path:
            schema_mismatches.append(
                {
                    "issue": "invalid_spec_endpoint",
                    "details": endpoint,
                }
            )
            continue

        checked_endpoints += 1
        url = f"{base_url}{path}"

        try:
            response = _call_endpoint(method, url)
        except requests.RequestException as exc:
            failing_endpoints.append(f"{method} {path}")
            schema_mismatches.append(
                {
                    "method": method,
                    "path": path,
                    "issue": "request_failed",
                    "details": str(exc),
                }
            )
            continue

        if response.status_code >= 400:
            failing_endpoints.append(f"{method} {path}")
            schema_mismatches.append(
                {
                    "method": method,
                    "path": path,
                    "issue": "http_error",
                    "status_code": response.status_code,
                    "body": _safe_text(response),
                }
            )
            continue

        try:
            actual_json = response.json()
        except json.JSONDecodeError:
            failing_endpoints.append(f"{method} {path}")
            schema_mismatches.append(
                {
                    "method": method,
                    "path": path,
                    "issue": "invalid_json",
                    "body": _safe_text(response),
                }
            )
            continue

        mismatches = validate_json_schema(expected_response, actual_json)
        if mismatches:
            failing_endpoints.append(f"{method} {path}")
            schema_mismatches.append(
                {
                    "method": method,
                    "path": path,
                    "expected_response": expected_response,
                    "actual_response": actual_json,
                    "mismatches": mismatches,
                }
            )

    goal_satisfied = len(failing_endpoints) == 0 and len(schema_mismatches) == 0

    return {
        "status": "success" if goal_satisfied else "failure",
        "goal_satisfied": goal_satisfied,
        "base_url": base_url,
        "checked_endpoints": checked_endpoints,
        "failing_endpoints": failing_endpoints,
        "schema_mismatches": schema_mismatches,
    }


def _call_endpoint(method: str, url: str) -> requests.Response:
    if method == "GET":
        return requests.get(url, timeout=10)
    if method == "POST":
        return requests.post(url, timeout=10)
    if method == "PUT":
        return requests.put(url, timeout=10)
    if method == "DELETE":
        return requests.delete(url, timeout=10)

    raise ValueError(f"Unsupported HTTP method: {method}")


def _safe_text(response: requests.Response) -> str:
    try:
        return response.text[:1000]
    except Exception:
        return "<unreadable_response_body>"
