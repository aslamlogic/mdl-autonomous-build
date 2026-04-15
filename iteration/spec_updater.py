"""
spec_updater.py

Deterministic Specification Evolution Engine

Purpose:
Transforms validation failures into explicit, append-only correction constraints.
Does NOT modify original intent fields.
Drives iterative convergence of the Meta Software Production System.
"""

from typing import Dict, List, Any


def update_spec_from_failures(spec: Dict[str, Any], validation_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point for spec evolution.

    Args:
        spec: Current working specification (dict)
        validation_report: Structured validation output from evaluator

    Returns:
        Updated specification with appended deterministic constraints
    """

    if not isinstance(spec, dict):
        raise ValueError("Spec must be a dictionary")

    if not isinstance(validation_report, dict):
        raise ValueError("Validation report must be a dictionary")

    findings = extract_findings(validation_report)
    constraints = map_findings_to_constraints(findings)

    updated_spec = append_constraints(spec, constraints)

    return updated_spec


# -------------------------------------------------------------------
# FINDING EXTRACTION
# -------------------------------------------------------------------

def extract_findings(validation_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract atomic findings from validation report.

    Expected structure:
    validation_report["findings"] = [
        {
            "finding_code": "...",
            "message": "...",
            "endpoint": {...},
            "details": {...}
        }
    ]
    """

    findings = validation_report.get("findings", [])

    if not isinstance(findings, list):
        return []

    return findings


# -------------------------------------------------------------------
# DETERMINISTIC MAPPING ENGINE
# -------------------------------------------------------------------

def map_findings_to_constraints(findings: List[Dict[str, Any]]) -> List[str]:
    """
    Convert validation findings into deterministic constraints.

    NO heuristics. Strict mapping only.
    """

    constraints = []

    for finding in findings:
        code = finding.get("finding_code", "")
        endpoint = finding.get("endpoint", {})
        details = finding.get("details", {})
        message = finding.get("message", "")

        constraint = None

        # ------------------------------------------------------------
        # SCHEMA MISMATCH
        # ------------------------------------------------------------
        if code == "schema_mismatch":
            method = endpoint.get("method", "UNKNOWN")
            path = endpoint.get("path", "UNKNOWN")
            constraint = f"Ensure {method} {path} response schema matches specification exactly"

        # ------------------------------------------------------------
        # MISSING ROUTE
        # ------------------------------------------------------------
        elif code == "missing_route":
            method = endpoint.get("method", "UNKNOWN")
            path = endpoint.get("path", "UNKNOWN")
            constraint = f"Add missing endpoint {method} {path}"

        # ------------------------------------------------------------
        # IMPORT ERROR
        # ------------------------------------------------------------
        elif code == "import_error":
            module = details.get("module", "unknown_module")
            constraint = f"Fix import error for module {module}"

        # ------------------------------------------------------------
        # RUNTIME ERROR
        # ------------------------------------------------------------
        elif code == "runtime_error":
            method = endpoint.get("method", "UNKNOWN")
            path = endpoint.get("path", "UNKNOWN")
            constraint = f"Ensure {method} {path} executes without runtime exception"

        # ------------------------------------------------------------
        # GOVERNANCE VIOLATION
        # ------------------------------------------------------------
        elif code == "governance_violation":
            constraint = "Ensure output contains code only with no commentary or markdown"

        # ------------------------------------------------------------
        # SECURITY VIOLATION
        # ------------------------------------------------------------
        elif code == "security_violation":
            constraint = "Remove unsafe operations, secrets, or unrestricted system calls"

        # ------------------------------------------------------------
        # DEPENDENCY ERROR
        # ------------------------------------------------------------
        elif code == "dependency_error":
            constraint = f"Fix dependency issue: {message}"

        # ------------------------------------------------------------
        # DEFAULT FALLBACK (STRICTLY CONTROLLED)
        # ------------------------------------------------------------
        else:
            constraint = f"Resolve validation issue: {message}"

        if constraint:
            constraints.append(constraint)

    return deduplicate_constraints(constraints)


# -------------------------------------------------------------------
# APPEND CONSTRAINTS (NON-DESTRUCTIVE)
# -------------------------------------------------------------------

def append_constraints(spec: Dict[str, Any], constraints: List[str]) -> Dict[str, Any]:
    """
    Append constraints to spec without overwriting original content.
    """

    updated_spec = dict(spec)  # shallow copy

    existing_constraints = updated_spec.get("constraints", [])

    if not isinstance(existing_constraints, list):
        existing_constraints = []

    combined = existing_constraints + constraints

    updated_spec["constraints"] = deduplicate_constraints(combined)

    return updated_spec


# -------------------------------------------------------------------
# UTILITY
# -------------------------------------------------------------------

def deduplicate_constraints(constraints: List[str]) -> List[str]:
    """
    Preserve order, remove duplicates.
    """

    seen = set()
    result = []

    for c in constraints:
        if c not in seen:
            seen.add(c)
            result.append(c)

    return result
