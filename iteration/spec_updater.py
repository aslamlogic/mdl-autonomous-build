def update_spec_with_failures(spec, evaluation):
    if not isinstance(spec, dict):
        spec = {}

    if "constraints" not in spec or not isinstance(spec["constraints"], list):
        spec["constraints"] = []

    logs = evaluation.get("logs", [])
    failing_endpoints = evaluation.get("failing_endpoints", [])

    for log in logs:
        if "app_not_callable" in log:
            constraint = {
                "type": "hard_requirement",
                "rule": "application_must_be_fastapi",
                "instruction": (
                    "The generated application MUST define:\n"
                    "from fastapi import FastAPI\n"
                    "app = FastAPI()\n"
                    "AND must expose 'app' as the ASGI callable.\n"
                    "DO NOT return dictionaries or non-callable objects."
                )
            }
            if constraint not in spec["constraints"]:
                spec["constraints"].append(constraint)

        if "unsupported_method" in log:
            constraint = {
                "type": "hard_requirement",
                "rule": "valid_http_methods",
                "instruction": (
                    "All endpoints MUST use valid HTTP methods: "
                    "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD."
                )
            }
            if constraint not in spec["constraints"]:
                spec["constraints"].append(constraint)

        if "SPEC FAIL → no endpoints defined" in log:
            constraint = {
                "type": "hard_requirement",
                "rule": "spec_must_define_endpoints",
                "instruction": (
                    "The specification MUST contain a non-empty `endpoints` list. "
                    "Generation must implement every endpoint declared in that list."
                )
            }
            if constraint not in spec["constraints"]:
                spec["constraints"].append(constraint)

    for failed in failing_endpoints:
        reason = failed.get("reason")
        method = failed.get("method", "GET")
        path = failed.get("path", "/health")

        if reason == "http_404":
            constraint = {
                "type": "hard_requirement",
                "rule": f"implement_{method}_{path}",
                "instruction": (
                    f"The application MUST implement endpoint:\n"
                    f"{method} {path}\n"
                    f"and return a JSON object."
                )
            }
            if constraint not in spec["constraints"]:
                spec["constraints"].append(constraint)

        if reason == "runtime_error":
            constraint = {
                "type": "hard_requirement",
                "rule": f"fix_runtime_for_{method}_{path}",
                "instruction": (
                    f"The endpoint {method} {path} MUST execute without runtime errors "
                    f"and return a valid JSON response."
                )
            }
            if constraint not in spec["constraints"]:
                spec["constraints"].append(constraint)

    return spec
