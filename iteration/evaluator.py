from fastapi.testclient import TestClient


def evaluate_system(app, spec: dict) -> dict:
    client = TestClient(app)

    logs = []
    failing_endpoints = []
    schema_mismatches = []

    endpoints = spec.get("endpoints", [])

    for ep in endpoints:
        method = ep.get("method", "").upper()
        path = ep.get("path", "")

        # Validate method
        if method not in ["GET", "POST", "PUT", "DELETE"]:
            msg = f"{method} {path} → FAIL (unsupported method)"
            logs.append(msg)
            failing_endpoints.append({
                "method": method,
                "path": path,
                "reason": "unsupported_method"
            })
            continue

        try:
            # Dispatch request
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path)
            elif method == "PUT":
                response = client.put(path)
            elif method == "DELETE":
                response = client.delete(path)

            status = response.status_code

            # Evaluate response
            if status >= 400:
                msg = f"{method} {path} → {status} (FAIL)"
                logs.append(msg)
                failing_endpoints.append({
                    "method": method,
                    "path": path,
                    "status": status
                })
            else:
                msg = f"{method} {path} → {status} (OK)"
                logs.append(msg)

        except Exception as e:
            msg = f"{method} {path} → ERROR ({str(e)})"
            logs.append(msg)
            failing_endpoints.append({
                "method": method,
                "path": path,
                "error": str(e)
            })

    # FINAL STATUS DECISION
    status = "failure" if failing_endpoints else "success"

    return {
        "status": status,
        "logs": logs,
        "failing_endpoints": failing_endpoints,
        "schema_mismatches": schema_mismatches
    }
