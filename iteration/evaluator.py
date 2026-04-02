import requests


def _compare_schema(expected: dict, actual: dict) -> bool:
    """
    Deterministic schema comparison supporting:
    1. Type-based schema (string, number, boolean, object, array)
    2. Literal value schema (e.g. "ok")
    """

    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return False

    for key, expected_value in expected.items():
        if key not in actual:
            return False

        actual_value = actual[key]

        # ---- TYPE-BASED SCHEMA ----
        if expected_value == "string":
            if not isinstance(actual_value, str):
                return False

        elif expected_value == "number":
            if not isinstance(actual_value, (int, float)):
                return False

        elif expected_value == "boolean":
            if not isinstance(actual_value, bool):
                return False

        elif expected_value == "object":
            if not isinstance(actual_value, dict):
                return False

        elif expected_value == "array":
            if not isinstance(actual_value, list):
                return False

        # ---- LITERAL VALUE SCHEMA ----
        else:
            if actual_value != expected_value:
                return False

    return True


def evaluate_system(spec: dict, base_url: str) -> dict:
    endpoints = spec.get("api", {}).get("endpoints", [])

    # ---- HARD RULE: EMPTY SYSTEM = FAILURE ----
    if not endpoints:
        return {
            "status": "failure",
            "goal_satisfied": False,
            "reason": "no endpoints defined",
            "base_url": base_url,
            "checked_endpoints": 0,
            "failing_endpoints": ["GET /health"],
            "schema_mismatches": [],
            "results": []
        }

    results = []
    failing = []
    schema_mismatches = []

    for ep in endpoints:
        method = ep.get("method", "GET").upper()
        path = ep.get("path", "/")
        expected_schema = ep.get("response_schema")

        url = f"{base_url}{path}"

        try:
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, json={})
            else:
                continue

            if response.status_code >= 400:
                failing.append(f"{method} {path}")
                results.append({
                    "endpoint": f"{method} {path}",
                    "status": "fail",
                    "code": response.status_code
                })
                continue

            try:
                data = response.json()
            except Exception:
                failing.append(f"{method} {path}")
                results.append({
                    "endpoint": f"{method} {path}",
                    "status": "fail",
                    "reason": "non-json response"
                })
                continue

            # ---- SCHEMA VALIDATION ----
            if expected_schema and not _compare_schema(expected_schema, data):
                failing.append(f"{method} {path}")
                schema_mismatches.append({
                    "method": method,
                    "path": path,
                    "expected_response": expected_schema,
                    "actual_response": data
                })

                results.append({
                    "endpoint": f"{method} {path}",
                    "status": "schema_mismatch",
                    "expected": expected_schema,
                    "actual": data
                })
            else:
                results.append({
                    "endpoint": f"{method} {path}",
                    "status": "pass",
                    "code": response.status_code
                })

        except Exception as e:
            failing.append(f"{method} {path}")
            results.append({
                "endpoint": f"{method} {path}",
                "status": "error",
                "error": str(e)
            })

    return {
        "status": "success" if not failing else "failure",
        "goal_satisfied": not failing,
        "base_url": base_url,
        "checked_endpoints": len(endpoints),
        "failing_endpoints": failing,
        "schema_mismatches": schema_mismatches,
        "results": results
    }
