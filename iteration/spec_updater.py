from copy import deepcopy


WRITE_METHODS = {"POST", "PUT", "PATCH"}


def _ensure_api_root(spec: dict) -> None:
    if "api" not in spec or not isinstance(spec["api"], dict):
        spec["api"] = {}
    if "endpoints" not in spec["api"] or not isinstance(spec["api"]["endpoints"], list):
        spec["api"]["endpoints"] = []


def _parse_endpoint_string(value: str) -> tuple[str, str]:
    parts = value.strip().split(maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Invalid endpoint format: {value}")
    method, path = parts[0].upper(), parts[1].strip()
    return method, path


def _find_endpoint(endpoints: list, method: str, path: str) -> dict | None:
    for endpoint in endpoints:
        if (
            isinstance(endpoint, dict)
            and endpoint.get("method", "").upper() == method.upper()
            and endpoint.get("path") == path
        ):
            return endpoint
    return None


def _default_endpoint(method: str, path: str) -> dict:
    return {
        "method": method,
        "path": path,
        "request_schema": {} if method in WRITE_METHODS else None,
        "response_schema": {"status": "string"},
    }


def _apply_missing_endpoints(spec: dict, evaluation: dict) -> None:
    endpoints = spec["api"]["endpoints"]
    for item in evaluation.get("failing_endpoints", []):
        method, path = _parse_endpoint_string(item)
        existing = _find_endpoint(endpoints, method, path)
        if existing is None:
            endpoints.append(_default_endpoint(method, path))


def _apply_schema_mismatches(spec: dict, evaluation: dict) -> None:
    endpoints = spec["api"]["endpoints"]
    for item in evaluation.get("schema_mismatches", []):
        method = item.get("method", "").upper()
        path = item.get("path")
        actual_response = item.get("actual_response")

        if not method or not path:
            continue

        endpoint = _find_endpoint(endpoints, method, path)
        if endpoint is None:
            endpoint = _default_endpoint(method, path)
            endpoints.append(endpoint)

        endpoint["response_schema"] = actual_response


def _apply_post_failures(spec: dict, evaluation: dict) -> None:
    endpoints = spec["api"]["endpoints"]
    for item in evaluation.get("post_failures", []):
        method = item.get("method", "").upper()
        path = item.get("path")

        if method != "POST" or not path:
            continue

        endpoint = _find_endpoint(endpoints, method, path)
        if endpoint is None:
            endpoint = _default_endpoint(method, path)
            endpoints.append(endpoint)

        if "request_schema" not in endpoint or endpoint["request_schema"] is None:
            endpoint["request_schema"] = {}


def update_spec(spec: dict, evaluation: dict) -> dict:
    """
    Deterministically update the spec based on evaluator output.

    Rules implemented:
    1. Missing endpoint -> add endpoint to spec.api.endpoints
    2. Response schema mismatch -> align response_schema to actual_response
    3. POST failure -> ensure POST endpoint has request_schema
    """
    updated = deepcopy(spec)
    _ensure_api_root(updated)

    _apply_missing_endpoints(updated, evaluation)
    _apply_schema_mismatches(updated, evaluation)
    _apply_post_failures(updated, evaluation)

    return updated
