"""
spec_updater.py

Deterministic Specification Evolution Engine

Aligned with existing controller import:
update_spec_with_failures()

Purpose:
Transforms validation failures into deterministic, append-only constraints.
"""

from typing import Dict, List, Any


# ================================================================
# PRIMARY ENTRYPOINT (MATCHES YOUR CONTROLLER)
# ================================================================

def update_spec_with_failures(spec: Dict[str, Any], validation_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entrypoint expected by controller.

    Args:
        spec: current specification
        validation_report: evaluator output

    Returns:
        updated spec with appended constraints
    """

    if not isinstance(spec, dict):
        raise ValueError("Spec must be dict")

    if not isinstance(validation_report, dict):
        return spec

    findings = extract_findings(validation_report)
    constraints = map_findings_to_constraints(findings)

    return append_constraints(spec, constraints)


# ================================================================
# FINDING EXTRACTION
# ================================================================

def extract_findings(validation_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Handles multiple possible report structures.
    """

    if "findings" in validation_report:
        return validation_report["findings"]

    if "validation_findings" in validation_report:
        return validation_report["validation_findings"]

    return []


# ================================================================
# DETERMINISTIC MAPPING
# ================================================================

def map_findings_to_constraints(findings: List[Dict[str, Any]]) -> List[str]:
    constraints = []

    for f in findings:
        code = f.get("finding_code", "")
        endpoint = f.get("endpoint", {})
        details = f.get("details", {})
        message = f.get("message", "")

        constraint = None

        # -------------------------------
        # SCHEMA
        # -------------------------------
        if code == "schema_mismatch":
            method = endpoint.get("method", "UNKNOWN")
            path = endpoint.get("path", "UNKNOWN")
            constraint = f"Ensure {method} {path} response matches schema"

        # -------------------------------
        # ROUTES
        # -------------------------------
        elif code == "missing_route":
            method = endpoint.get("method", "UNKNOWN")
            path = endpoint.get("path", "UNKNOWN")
            constraint = f"Add endpoint {method} {path}"

        # -------------------------------
        # IMPORTS
        # -------------------------------
        elif code == "import_error":
            module = details.get("module", "unknown")
            constraint = f"Fix import error for {module}"

        # -------------------------------
        # RUNTIME
        # -------------------------------
        elif code == "runtime_error":
            method = endpoint.get("method", "UNKNOWN")
            path = endpoint.get("path", "UNKNOWN")
            constraint = f"Ensure {method} {path} runs without exception"

        # -------------------------------
        # GOVERNANCE
        # -------------------------------
        elif code == "governance_violation":
            constraint = "Output must contain code only with no commentary"

        # -------------------------------
        # SECURITY
        # -------------------------------
        elif code == "security_violation":
            constraint = "Remove unsafe operations and secrets"

        # -------------------------------
        # DEPENDENCY
        # -------------------------------
        elif code == "dependency_error":
            constraint = f"Fix dependency issue: {message}"

        # -------------------------------
        # FALLBACK
        # -------------------------------
        else:
            if message:
                constraint = f"Resolve issue: {message}"

        if constraint:
            constraints.append(constraint)

    return dedupe(constraints)


# ================================================================
# APPEND CONSTRAINTS (NON-DESTRUCTIVE)
# ================================================================

def append_constraints(spec: Dict[str, Any], constraints: List[str]) -> Dict[str, Any]:
    updated = dict(spec)

    existing = updated.get("constraints", [])

    if not isinstance(existing, list):
        existing = []

    combined = existing + constraints
    updated["constraints"] = dedupe(combined)

    return updated


# ================================================================
# UTILITY
# ================================================================

def dedupe(items: List[str]) -> List[str]:
    seen = set()
    result = []

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result
