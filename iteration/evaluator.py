def _matches_type(expected, actual):
    mapping = {
        "string": str,
        "number": (int, float),
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    return isinstance(actual, mapping.get(expected, object))


def evaluate_system(spec: dict):
    endpoints = spec.get("endpoints", [])

    checked = 0
    failing = []
    mismatches = []

    for ep in endpoints:
        method = ep.get("method")
        path = ep.get("path")
        expected = ep.get("response", {})

        checked += 1

        # Simulated system behaviour (deterministic)
        if method == "GET" and path == "/health":
            actual = {"status": 1}
        else:
            failing.append(f"{method} {path}")
            continue

        for key, expected_type in expected.items():
            actual_value = actual.get(key)

            if not _matches_type(expected_type, actual_value):
                mismatches.append({
                    "endpoint": f"{method} {path}",
                    "expected": expected,
                    "actual": actual
                })
                failing.append(f"{method} {path}")

    if not failing and not mismatches:
        return {
            "status": "success",
            "goal_satisfied": True,
            "base_url": "http://localhost:8000",
            "checked_endpoints": checked,
            "failing_endpoints": [],
            "schema_mismatches": [],
        }

    return {
        "status": "failure",
        "goal_satisfied": False,
        "base_url": "http://localhost:8000",
        "checked_endpoints": checked,
        "failing_endpoints": failing,
        "schema_mismatches": mismatches,
    }
