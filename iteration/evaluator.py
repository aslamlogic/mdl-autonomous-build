import requests


def _compare_schema(expected: dict, actual: dict) -> bool:
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return False

    for key in expected.keys():
        if key not in actual:
            return False

    return True


def evaluate_system(spec: dict, base_url: str) -> dict:
    endpoints = spec.get("api", {}).get("endpoints", [])

    if not endpoints:
        return {
            "status": "failure",
            "goal_satisfied": False,
            "reason": "no endpoints defined",
            "base_url": base_url,
            "checked_endpoints": 0,
            "failing_endpoints": ["GET /health"],
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
