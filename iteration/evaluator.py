import ast
import json
import os
from typing import Any, Dict, List


REPORT_PATH = "reports/validation_default_run.json"


def _ensure_reports_dir() -> None:
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)


def _add_finding(
    findings: List[Dict[str, Any]],
    *,
    category: str,
    message: str,
    path: str,
    failure_code: str,
) -> None:
    findings.append(
        {
            "category": category,
            "message": message,
            "path": path,
            "failure_code": failure_code,
        }
    )


def _path_exists(path: str) -> bool:
    return os.path.exists(path)


def _read_file(path: str) -> str:
    if not _path_exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _syntax_check(main_content: str, findings: List[Dict[str, Any]]) -> None:
    if not main_content.strip():
        _add_finding(
            findings,
            category="STRUCTURE",
            message="No application source code found for evaluation",
            path="generated_app/main.py",
            failure_code="E-STRUCTURE",
        )
        return

    try:
        ast.parse(main_content)
    except SyntaxError as e:
        _add_finding(
            findings,
            category="SYNTAX",
            message=f"Syntax error: {e.msg} at line {e.lineno}",
            path="generated_app/main.py",
            failure_code="E-SYNTAX",
        )


def _structure_check(findings: List[Dict[str, Any]]) -> None:
    if not _path_exists("meta_ui/api.py"):
        _add_finding(
            findings,
            category="STRUCTURE",
            message="Required file missing: meta_ui/api.py",
            path="meta_ui/api.py",
            failure_code="E-STRUCTURE",
        )

    if not _path_exists("apps"):
        _add_finding(
            findings,
            category="STRUCTURE",
            message="apps/ directory missing",
            path="apps/",
            failure_code="E-STRUCTURE",
        )

    if not (_path_exists("generated_app/main.py") or _path_exists("apps/generated_app/main.py")):
        _add_finding(
            findings,
            category="STRUCTURE",
            message="No generated main application file found",
            path="generated_app/main.py",
            failure_code="E-STRUCTURE",
        )


def _behaviour_check(main_content: str, findings: List[Dict[str, Any]]) -> None:
    api_source = _read_file("meta_ui/api.py")
    combined = "\n".join([main_content, api_source])

    if not api_source.strip():
        _add_finding(
            findings,
            category="BEHAVIOUR",
            message="Cannot run behaviour checks because meta_ui/api.py is missing",
            path="meta_ui/api.py",
            failure_code="E-BEHAVIOUR",
        )
        return

    if "/health" not in combined:
        _add_finding(
            findings,
            category="BEHAVIOUR",
            message="Required /health endpoint not found",
            path="meta_ui/api.py",
            failure_code="E-BEHAVIOUR",
        )

    if '"status": "ok"' not in combined and "'status': 'ok'" not in combined and "'status': \"ok\"" not in combined:
        _add_finding(
            findings,
            category="BEHAVIOUR",
            message='Required /health response {"status": "ok"} not found',
            path="meta_ui/api.py",
            failure_code="E-BEHAVIOUR",
        )


def _lwp_check(findings: List[Dict[str, Any]]) -> None:
    if not _path_exists("iteration/rule_applicator.py"):
        _add_finding(
            findings,
            category="LWP",
            message="rule_applicator.py missing; deterministic LWP chain cannot be confirmed",
            path="iteration/rule_applicator.py",
            failure_code="E-LWP",
        )


def _ui_check(findings: List[Dict[str, Any]]) -> None:
    api_source = _read_file("meta_ui/api.py")

    if not api_source.strip():
        _add_finding(
            findings,
            category="UI",
            message="Required UI-related file missing: meta_ui/api.py",
            path="meta_ui/api.py",
            failure_code="E-UI",
        )
        return

    if "UI_MARKER" not in api_source:
        _add_finding(
            findings,
            category="UI",
            message="No expected UI markers found in codebase",
            path="workspace",
            failure_code="E-UI",
        )


def evaluate(main_content: str) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []

    _syntax_check(main_content, findings)
    _structure_check(findings)
    _behaviour_check(main_content, findings)
    _lwp_check(findings)
    _ui_check(findings)

    result: Dict[str, Any] = {
        "passed": len(findings) == 0,
        "findings": findings,
        "report_path": REPORT_PATH,
    }

    _ensure_reports_dir()
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result
