"""
iteration/evaluator.py

HARDENED deterministic validation engine

Upgrades:
---------
1. Strict import + syntax enforcement
2. Mandatory FastAPI app detection
3. Route coverage scoring vs spec
4. Runtime execution checks (multiple endpoints)
5. Strict schema validation (type + required fields)
6. Failure taxonomy expansion (deterministic)
7. Non-ambiguous machine-readable outputs
8. Backward compatibility with controller (evaluate_app)

This is now a TRUE gatekeeper — bad systems do not pass.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient


# ============================================================
# ENTRYPOINTS (COMPATIBILITY)
# ============================================================

def evaluate_app(spec: Optional[Dict[str, Any]] = None, base_dir: str = ".") -> Dict[str, Any]:
    return run_validation(spec, base_dir)


def evaluate_system(spec: Optional[Dict[str, Any]] = None, base_dir: str = ".") -> Dict[str, Any]:
    return run_validation(spec, base_dir)


def validate_system(spec: Optional[Dict[str, Any]] = None, base_dir: str = ".") -> Dict[str, Any]:
    return run_validation(spec, base_dir)


# ============================================================
# MAIN VALIDATION
# ============================================================

def run_validation(spec: Optional[Dict[str, Any]] = None, base_dir: str = ".") -> Dict[str, Any]:

    repo_root = Path(base_dir).resolve()
    findings: List[Dict[str, Any]] = []

    declared_endpoints = extract_spec_endpoints(spec)

    # ------------------------------------------------------------
    # LOAD APP (STRICT)
    # ------------------------------------------------------------
    load = load_app(repo_root)

    if not load["success"]:
        findings.append(finding(load["error_type"], load["error_message"]))
        return build_report(False, findings, declared_endpoints, [])

    app = load["app"]

    # ------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------
    routes = get_routes(app)

    if not routes:
        findings.append(finding("structure_error", "No routes detected in application"))

    # ------------------------------------------------------------
    # ROUTE COVERAGE
    # ------------------------------------------------------------
    coverage_findings = check_route_coverage(declared_endpoints, routes)
    findings.extend(coverage_findings)

    # ------------------------------------------------------------
    # MANDATORY HEALTH CHECK
    # ------------------------------------------------------------
    if not route_exists(routes, "GET", "/health"):
        findings.append(finding("missing_route", "Missing GET /health"))

    # ------------------------------------------------------------
    # RUNTIME TESTS
    # ------------------------------------------------------------
    runtime_findings = runtime_validation(app, declared_endpoints, routes)
    findings.extend(runtime_findings)

    overall_pass = not any(f["severity"] == "error" for f in findings)

    return build_report(overall_pass, findings, declared_endpoints, routes)


# ============================================================
# APP LOADING (STRICT)
# ============================================================

def load_app(repo_root: Path):

    sys.path.insert(0, str(repo_root))

    modules = ["generated_app.main", "app.main", "main"]

    last_error = None

    for m in modules:
        try:
            mod = importlib.import_module(m)
            app = getattr(mod, "app", None)

            if app is None:
                last_error = f"{m} has no app"
                continue

            return {"success": True, "app": app}

        except Exception as e:
            last_error = str(e)

    return {
        "success": False,
        "error_type": "import_error",
        "error_message": last_error or "Failed to import app"
    }


# ============================================================
# ROUTES
# ============================================================

def get_routes(app):

    routes = []

    for r in app.routes:
        if hasattr(r, "methods"):
            for m in r.methods:
                if m not in ["HEAD", "OPTIONS"]:
                    routes.append({
                        "method": m,
                        "path": r.path
                    })

    return dedupe(routes)


def route_exists(routes, method, path):
    return any(r["method"] == method and r["path"] == path for r in routes)


def dedupe(routes):
    seen = set()
    out = []

    for r in routes:
        key = (r["method"], r["path"])
        if key not in seen:
            seen.add(key)
            out.append(r)

    return out


# ============================================================
# SPEC EXTRACTION
# ============================================================

def extract_spec_endpoints(spec):

    if not isinstance(spec, dict):
        return []

    candidates = []

    if isinstance(spec.get("endpoints"), list):
        candidates = spec["endpoints"]
    elif isinstance(spec.get("routes"), list):
        candidates = spec["routes"]
    elif isinstance(spec.get("api"), dict):
        candidates = spec["api"].get("endpoints", [])

    endpoints = []

    for e in candidates:
        if not isinstance(e, dict):
            continue

        path = e.get("path")
        method = str(e.get("method", "GET")).upper()

        if not isinstance(path, str) or not path.startswith("/"):
            continue

        endpoints.append({
            "method": method,
            "path": path,
            "schema": e.get("response_schema")
        })

    return endpoints


# ============================================================
# ROUTE COVERAGE
# ============================================================

def check_route_coverage(spec_eps, routes):

    findings = []

    for ep in spec_eps:
        if not route_exists(routes, ep["method"], ep["path"]):
            findings.append(
                finding("missing_route", f"{ep['method']} {ep['path']} missing")
            )

    return findings


# ============================================================
# RUNTIME VALIDATION
# ============================================================

def runtime_validation(app, spec_eps, routes):

    findings = []
    client = TestClient(app)

    # always test /health if exists
    if route_exists(routes, "GET", "/health"):
        findings.extend(test_endpoint(client, "GET", "/health", None))

    for ep in spec_eps:
        if ep["method"] != "GET":
            continue

        if not route_exists(routes, ep["method"], ep["path"]):
            continue

        findings.extend(test_endpoint(client, ep["method"], ep["path"], ep["schema"]))

    return findings


def test_endpoint(client, method, path, schema):

    findings = []

    try:
        r = client.get(path)
    except Exception as e:
        return [finding("runtime_error", str(e))]

    if r.status_code >= 400:
        return [finding("runtime_error", f"{path} returned {r.status_code}")]

    try:
        data = r.json()
    except Exception:
        return [finding("schema_mismatch", f"{path} not JSON")]

    schema_error = validate_schema(data, schema, path)

    if schema_error:
        findings.append(schema_error)

    return findings


# ============================================================
# SCHEMA VALIDATION (STRICTER)
# ============================================================

def validate_schema(data, schema, path):

    if not schema:
        return None

    if not isinstance(schema, dict):
        return None

    if schema.get("type") == "object" and not isinstance(data, dict):
        return finding("schema_mismatch", f"{path} not object")

    if schema.get("type") == "array" and not isinstance(data, list):
        return finding("schema_mismatch", f"{path} not array")

    required = schema.get("required", [])

    if isinstance(data, dict):
        for key in required:
            if key not in data:
                return finding("schema_mismatch", f"{path} missing {key}")

    props = schema.get("properties", {})

    for k, rule in props.items():
        if k not in data:
            continue

        if not type_match(data[k], rule.get("type")):
            return finding("schema_mismatch", f"{path}.{k} wrong type")

    return None


def type_match(v, t):
    mapping = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "object": dict,
        "array": list,
    }

    if t not in mapping:
        return True

    return isinstance(v, mapping[t])


# ============================================================
# REPORT
# ============================================================

def build_report(pass_state, findings, spec_eps, routes):

    return {
        "overall_pass": pass_state,
        "validation_findings": findings,
        "findings": findings,
        "route_coverage_pct": coverage(spec_eps, routes),
        "declared_endpoints": spec_eps,
        "actual_routes": routes,
        "summary_json": {
            "overall_pass": pass_state,
            "error_count": sum(1 for f in findings if f["severity"] == "error"),
            "finding_count": len(findings)
        }
    }


def coverage(spec_eps, routes):
    if not spec_eps:
        return 100.0

    ok = sum(1 for e in spec_eps if route_exists(routes, e["method"], e["path"]))
    return round((ok / len(spec_eps)) * 100, 2)


# ============================================================
# UTIL
# ============================================================

def finding(code, msg):
    return {
        "finding_code": code,
        "severity": "error",
        "message": msg
    }
