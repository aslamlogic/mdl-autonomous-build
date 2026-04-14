def update_spec_with_failures(spec, evaluation):
    """
    Stage 1 — Spec Evolution Engine

    Converts failures into deterministic spec improvements.
    """

    if not isinstance(spec, dict):
        spec = {}

    if "constraints" not in spec:
        spec["constraints"] = []

    if "endpoints" not in spec:
        spec["endpoints"] = []

    logs = evaluation.get("logs", [])
    failing_endpoints = evaluation.get("failing_endpoints", [])

    # ============================================================
    # 1. HARD FAILURE: NO ENDPOINTS → CREATE BASELINE
    # ============================================================
    if "SPEC FAIL → no endpoints defined" in logs:
        spec["endpoints"] = [
            {"method": "GET", "path": "/health"}
        ]

        spec["constraints"].append({
            "type": "bootstrap",
            "instruction": "System must define at least one endpoint. Added /health."
        })

        return spec

    # ============================================================
    # 2. APP FAILURE → FORCE FASTAPI CONTRACT
    # ============================================================
    for log in logs:
        if "app_not_callable" in log:
            constraint = {
                "type": "hard_requirement",
                "rule": "fastapi_app_required",
                "instruction": (
                    "Application MUST define:\n"
                    "from fastapi import FastAPI\n"
                    "app = FastAPI()\n"
                    "and expose `app` as callable."
                )
            }
            if constraint not in spec["constraints"]:
                spec["constraints"].append(constraint)

    # ============================================================
    # 3. ENDPOINT FAILURES → SPEC EXPANSION
    # ============================================================
    for failure in failing_endpoints:

        method = failure.get("method", "GET")
        path = failure.get("path", "/health")
        reason = failure.get("reason")

        # --- Missing endpoint (404) ---
        if reason == "http_404":
            if not any(e["path"] == path for e in spec["endpoints"]):
                spec["endpoints"].append({
                    "method": method,
                    "path": path
                })

            spec["constraints"].append({
                "type": "endpoint_requirement",
                "instruction": f"Implement endpoint {method} {path}"
            })

        # --- Runtime error ---
        if reason == "runtime_error":
            spec["constraints"].append({
                "type": "stability_requirement",
                "instruction": f"Endpoint {method} {path} must execute without errors"
            })

        # --- Invalid method ---
        if reason == "unsupported_method":
            spec["constraints"].append({
                "type": "method_constraint",
                "instruction": (
                    "Use only valid HTTP methods: GET, POST, PUT, DELETE, PATCH"
                )
            })

    # ============================================================
    # 4. GUARANTEE MINIMUM VIABLE SPEC
    # ============================================================
    if not spec["endpoints"]:
        spec["endpoints"].append({
            "method": "GET",
            "path": "/health"
        })

    return spec
