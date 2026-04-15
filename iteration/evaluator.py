"""
iteration/evaluator.py

Deterministic validation engine for the Meta Dev Launcher.

Purpose
-------
1. Validate generated Python application code after write.
2. Enforce syntax, import, structural, route, runtime, and schema checks.
3. Return machine-readable findings for the spec evolution engine.
4. Provide backward-compatible entrypoints for existing controller flows.

Design principles
-----------------
- Deterministic result structure
- No narrative-only failures
- Validation findings are atomic and machine-consumable
- Multiple entrypoints provided to reduce integration risk
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi.testclient import TestClient


# ============================================================
# PUBLIC API — BACKWARD-COMPATIBLE ENTRYPOINTS
# ============================================================

def evaluate_system(spec: Optional[Dict[str, Any]] = None, base_dir: str = ".") -> Dict[str, Any]:
    """
    Backward-compatible entrypoint.

    Parameters
    ----------
    spec:
        The current normalized or raw specification dict.
    base_dir:
        Repository root path.

    Returns
    -------
    Structured validation report.
    """
    return run_validation(spec=spec, base_dir=base_dir)


def validate_system(spec: Optional[Dict[str, Any]] = None, base_dir: str = ".") -> Dict[str, Any]:
    """
    Alternate entrypoint used by some controller variants.
    """
    return run_validation(spec=spec, base_dir=base_dir)


def evaluate_candidate(spec: Optional[Dict[str, Any]] = None, base_dir: str = ".") -> Dict[str, Any]:
    """
    Alternate entrypoint used by some controller variants.
    """
    return run_validation(spec=spec, base_dir=base_dir)


# ============================================================
# MAIN VALIDATION PIPELINE
# ============================================================

def run_validation(spec: Optional[Dict[str, Any]] = None, base_dir: str = ".") -> Dict[str, Any]:
    repo_root = Path(base_dir).resolve()

    findings: List[Dict[str, Any]] = []
    declared_endpoints = _extract_declared_endpoints(spec)

    import_result = _load_generated_app(repo_root)
    if not import_result["success"]:
        findings.append(
            _finding(
                finding_code=import_result["error_type"],
                severity="error",
                message=import_result["error_message"],
                details=import_result.get("diagnostics", {}),
            )
        )
        return _build_report(
            overall_pass=False,
            findings=findings,
            declared_endpoints=declared_endpoints,
            actual_routes=[],
        )

    app = import_result["app"]
    actual_routes = _collect_routes(app)

    # ------------------------------------------------------------
    # Structural check: FastAPI app exists
    # ------------------------------------------------------------
    if app is None:
        findings.append(
            _finding(
                finding_code="structure_error",
                severity="error",
                message="Generated application object is missing",
            )
        )
        return _build_report(
            overall_pass=False,
            findings=findings,
            declared_endpoints=declared_endpoints,
            actual_routes=actual_routes,
        )

    # ------------------------------------------------------------
    # Route presence checks
    # ------------------------------------------------------------
    route_findings = _validate_route_presence(declared_endpoints, actual_routes)
    findings.extend(route_findings)

    # ------------------------------------------------------------
    # Mandatory /health check, even if spec is vague
    # ------------------------------------------------------------
    if not _route_exists(actual_routes, "GET", "/health"):
        findings.append(
            _finding(
                finding_code="missing_route",
                severity="error",
                message="Missing mandatory health route GET /health",
                endpoint={"method": "GET", "path": "/health"},
            )
        )

    # ------------------------------------------------------------
    # Runtime and schema checks
    # ------------------------------------------------------------
    runtime_findings = _validate_runtime_behaviour(app, declared_endpoints, actual_routes)
    findings.extend(runtime_findings)

    overall_pass = not any(item["severity"] == "error" for item in findings)

    return _build_report(
        overall_pass=overall_pass,
        findings=findings,
        declared_endpoints=declared_endpoints,
        actual_routes=actual_routes,
    )


# ============================================================
# APP LOADING
# ============================================================

def _load_generated_app(repo_root: Path) -> Dict[str, Any]:
    """
    Load the generated FastAPI application from common entrypoint paths.

    Supported candidates:
    - generated_app.main:app
    - app.main:app
    - src.main:app
    - main:app
    """
    module_candidates = [
        "generated_app.main",
        "app.main",
        "src.main",
        "main",
    ]

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    last_error: Optional[Exception] = None

    for module_name in module_candidates:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            last_error = exc
            continue

        app = getattr(module, "app", None)
        if app is None:
            last_error = AttributeError(f"Module '{module_name}' has no attribute 'app'")
            continue

        return {
            "success": True,
            "module_name": module_name,
            "app": app,
            "diagnostics": {"module_name": module_name},
        }

    error_message = "Failed to import generated FastAPI app"
    diagnostics: Dict[str, Any] = {}

    if last_error is not None:
        error_type = _classify_import_exception(last_error)
        error_message = str(last_error)
        diagnostics = {"exception_class": last_error.__class__.__name__}
    else:
        error_type = "import_error"

    return {
        "success": False,
        "error_type": error_type,
        "error_message": error_message,
        "diagnostics": diagnostics,
    }


def _classify_import_exception(exc: Exception) -> str:
    name = exc.__class__.__name__
    if name == "SyntaxError":
        return "syntax_error"
    if name in {"ModuleNotFoundError", "ImportError"}:
        return "import_error"
    return "dependency_error"


# ============================================================
# ROUTE EXTRACTION
# ============================================================

def _collect_routes(app: Any) -> List[Dict[str, str]]:
    routes: List[Dict[str, str]] = []

    for route in getattr(app, "routes", []):
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)

        if not path or not methods:
            continue

        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes.append(
                {
                    "method": str(method).upper(),
                    "path": str(path),
                }
            )

    return _dedupe_routes(routes)


def _dedupe_routes(routes: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    result = []

    for item in routes:
        key = (item["method"], item["path"])
        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


# ============================================================
# SPEC ENDPOINT EXTRACTION
# ============================================================

def _extract_declared_endpoints(spec: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Accept multiple possible spec shapes.

    Supported examples:
    1. {"endpoints": [{"method": "GET", "path": "/health", "response_schema": {...}}]}
    2. {"api": {"endpoints": [...]}}
    3. {"routes": [...]}
    4. None -> []
    """
    if not isinstance(spec, dict):
        return []

    candidates: List[Any] = []

    if isinstance(spec.get("endpoints"), list):
        candidates = spec["endpoints"]
    elif isinstance(spec.get("routes"), list):
        candidates = spec["routes"]
    elif isinstance(spec.get("api"), dict) and isinstance(spec["api"].get("endpoints"), list):
        candidates = spec["api"]["endpoints"]

    normalized: List[Dict[str, Any]] = []

    for item in candidates:
        if not isinstance(item, dict):
            continue

        method = str(item.get("method", "GET")).upper()
        path = item.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            continue

        normalized.append(
            {
                "method": method,
                "path": path,
                "request_schema": item.get("request_schema"),
                "response_schema": item.get("response_schema"),
            }
        )

    return normalized


# ============================================================
# ROUTE PRESENCE VALIDATION
# ============================================================

def _validate_route_presence(
    declared_endpoints: List[Dict[str, Any]],
    actual_routes: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    for endpoint in declared_endpoints:
        method = endpoint["method"]
        path = endpoint["path"]

        if not _route_exists(actual_routes, method, path):
            findings.append(
                _finding(
                    finding_code="missing_route",
                    severity="error",
                    message=f"Missing declared endpoint {method} {path}",
                    endpoint={"method": method, "path": path},
                )
            )

    return findings


def _route_exists(actual_routes: List[Dict[str, str]], method: str, path: str) -> bool:
    target = (method.upper(), path)
    return any((item["method"], item["path"]) == target for item in actual_routes)


# ============================================================
# RUNTIME VALIDATION
# ============================================================

def _validate_runtime_behaviour(
    app: Any,
    declared_endpoints: List[Dict[str, Any]],
    actual_routes: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    client = TestClient(app)

    # Always test /health if present
    if _route_exists(actual_routes, "GET", "/health"):
        findings.extend(
            _runtime_check_single_endpoint(
                client=client,
                endpoint={
                    "method": "GET",
                    "path": "/health",
                    "response_schema": {"type": "object"},
                },
            )
        )

    # Test declared GET endpoints only. Deterministic and safe.
    for endpoint in declared_endpoints:
        if endpoint["method"] != "GET":
            continue

        if not _route_exists(actual_routes, endpoint["method"], endpoint["path"]):
            continue

        findings.extend(
            _runtime_check_single_endpoint(
                client=client,
                endpoint=endpoint,
            )
        )

    return findings


def _runtime_check_single_endpoint(client: TestClient, endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    method = endpoint["method"]
    path = endpoint["path"]
    response_schema = endpoint.get("response_schema")

    try:
        if method == "GET":
            response = client.get(path)
        else:
            return findings

    except Exception as exc:
        findings.append(
            _finding(
                finding_code="runtime_error",
                severity="error",
                message=f"Runtime exception for {method} {path}: {exc}",
                endpoint={"method": method, "path": path},
                details={"exception_class": exc.__class__.__name__},
            )
        )
        return findings

    if response.status_code >= 500:
        findings.append(
            _finding(
                finding_code="runtime_error",
                severity="error",
                message=f"{method} {path} returned server error {response.status_code}",
                endpoint={"method": method, "path": path},
                details={"status_code": response.status_code},
            )
        )
        return findings

    if response.status_code >= 400:
        findings.append(
            _finding(
                finding_code="runtime_error",
                severity="error",
                message=f"{method} {path} returned client/server error {response.status_code}",
                endpoint={"method": method, "path": path},
                details={"status_code": response.status_code},
            )
        )
        return findings

    try:
        payload = response.json()
    except Exception as exc:
        findings.append(
            _finding(
                finding_code="schema_mismatch",
                severity="error",
                message=f"{method} {path} did not return JSON",
                endpoint={"method": method, "path": path},
                details={"exception_class": exc.__class__.__name__},
            )
        )
        return findings

    schema_error = _validate_response_schema(payload, response_schema, method, path)
    if schema_error is not None:
        findings.append(schema_error)

    return findings


# ============================================================
# SCHEMA VALIDATION
# ============================================================

def _validate_response_schema(
    payload: Any,
    response_schema: Any,
    method: str,
    path: str,
) -> Optional[Dict[str, Any]]:
    """
    Conservative schema checks only.

    Supported patterns:
    1. None -> no schema enforcement
    2. {"type": "object"} -> payload must be dict
    3. {"type": "array"} -> payload must be list
    4. {"required": ["a", "b"]} -> payload dict must include keys
    5. {"properties": {"status": {"type": "string"}}}
    """
    if response_schema is None:
        return None

    if not isinstance(response_schema, dict):
        return None

    declared_type = response_schema.get("type")
    required = response_schema.get("required", [])
    properties = response_schema.get("properties", {})

    if declared_type == "object" and not isinstance(payload, dict):
        return _finding(
            finding_code="schema_mismatch",
            severity="error",
            message=f"{method} {path} response is not an object",
            endpoint={"method": method, "path": path},
            actual_value=_safe_json(payload),
            expected_value=_safe_json(response_schema),
        )

    if declared_type == "array" and not isinstance(payload, list):
        return _finding(
            finding_code="schema_mismatch",
            severity="error",
            message=f"{method} {path} response is not an array",
            endpoint={"method": method, "path": path},
            actual_value=_safe_json(payload),
            expected_value=_safe_json(response_schema),
        )

    if required and isinstance(payload, dict):
        missing = [key for key in required if key not in payload]
        if missing:
            return _finding(
                finding_code="schema_mismatch",
                severity="error",
                message=f"{method} {path} missing required keys: {', '.join(missing)}",
                endpoint={"method": method, "path": path},
                actual_value=_safe_json(payload),
                expected_value=_safe_json(response_schema),
            )

    if properties and isinstance(payload, dict):
        for key, rule in properties.items():
            if key not in payload:
                continue

            expected_type = None
            if isinstance(rule, dict):
                expected_type = rule.get("type")

            if expected_type is None:
                continue

            if not _matches_declared_type(payload[key], expected_type):
                return _finding(
                    finding_code="schema_mismatch",
                    severity="error",
                    message=f"{method} {path} key '{key}' has wrong type",
                    endpoint={"method": method, "path": path},
                    actual_value=_safe_json(payload),
                    expected_value=_safe_json(response_schema),
                )

    return None


def _matches_declared_type(value: Any, expected_type: str) -> bool:
    mapping = {
        "string": lambda v: isinstance(v, str),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "null": lambda v: v is None,
    }

    checker = mapping.get(expected_type)
    if checker is None:
        return True

    return checker(value)


# ============================================================
# REPORT BUILDING
# ============================================================

def _build_report(
    overall_pass: bool,
    findings: List[Dict[str, Any]],
    declared_endpoints: List[Dict[str, Any]],
    actual_routes: List[Dict[str, str]],
) -> Dict[str, Any]:
    route_coverage_pct = _compute_route_coverage_pct(declared_endpoints, actual_routes)

    summary = {
        "overall_pass": overall_pass,
        "finding_count": len(findings),
        "error_count": sum(1 for item in findings if item["severity"] == "error"),
        "warning_count": sum(1 for item in findings if item["severity"] == "warning"),
        "route_coverage_pct": route_coverage_pct,
        "declared_route_count": len(declared_endpoints),
        "actual_route_count": len(actual_routes),
    }

    return {
        "overall_pass": overall_pass,
        "validation_findings": findings,
        "findings": findings,
        "route_coverage_pct": route_coverage_pct,
        "declared_endpoints": declared_endpoints,
        "actual_routes": actual_routes,
        "summary_json": summary,
    }


def _compute_route_coverage_pct(
    declared_endpoints: List[Dict[str, Any]],
    actual_routes: List[Dict[str, str]],
) -> float:
    if not declared_endpoints:
        return 100.0

    matched = 0
    for endpoint in declared_endpoints:
        if _route_exists(actual_routes, endpoint["method"], endpoint["path"]):
            matched += 1

    return round((matched / len(declared_endpoints)) * 100, 2)


# ============================================================
# FINDING FORMAT
# ============================================================

def _finding(
    finding_code: str,
    severity: str,
    message: str,
    endpoint: Optional[Dict[str, str]] = None,
    details: Optional[Dict[str, Any]] = None,
    actual_value: Optional[str] = None,
    expected_value: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "finding_code": finding_code,
        "severity": severity,
        "message": message,
        "endpoint": endpoint or {},
        "details": details or {},
        "actual_value": actual_value,
        "expected_value": expected_value,
    }


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value)


# ============================================================
# OPTIONAL DEBUG ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    result = run_validation(spec=None, base_dir=".")
    print(json.dumps(result, indent=2))
