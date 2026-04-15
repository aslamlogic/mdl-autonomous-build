"""
iteration/controller.py

Deterministic run isolation controller for the Meta Dev Launcher.

Purpose
-------
1. Execute the full generation -> write -> validate -> deploy loop.
2. Isolate every run into its own /runs/{run_id}/ directory.
3. Persist spec snapshots, validation reports, deployment results, and logs.
4. Preserve backward compatibility with existing imports:
   - run_iteration_loop
   - main

Directory layout
----------------
runs/
  {run_id}/
    spec_initial.json
    spec_final.json
    run_summary.json
    event_log.json
    iterations/
      iteration_1/
        spec_before.json
        generation_result.json
        write_result.json
        validation_report.json
        deployment_result.json
        spec_after.json
      iteration_2/
        ...

Notes
-----
- Generated application files are still written to the repository root by the
  file writer so that validation and deployment continue to work with the
  existing system structure.
- Run isolation here is for audit, replay, forensic debugging, and future
  parallelisation readiness.
"""

from __future__ import annotations

import json
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from iteration.deploy import deploy_system
from iteration.evaluator import evaluate_app
from iteration.file_writer import write_files
from iteration.spec_updater import update_spec_with_failures

try:
    from engine.llm_interface import generate_code
except Exception:
    generate_code = None  # type: ignore

try:
    from iteration.prompt_builder import build_prompt
except Exception:
    build_prompt = None  # type: ignore


# ============================================================
# CONFIG
# ============================================================

DEFAULT_MAX_ITERATIONS = 3
RUNS_DIR_NAME = "runs"


# ============================================================
# PUBLIC API
# ============================================================

def run_iteration_loop(
    spec: Dict[str, Any],
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    base_dir: str = ".",
) -> Dict[str, Any]:
    """
    Backward-compatible main controller entrypoint.

    Parameters
    ----------
    spec:
        Input specification dict.
    max_iterations:
        Maximum number of correction cycles.
    base_dir:
        Repository root.

    Returns
    -------
    Structured run summary.
    """
    repo_root = Path(base_dir).resolve()
    run_id = generate_run_id()
    run_root = prepare_run_directory(repo_root, run_id)

    event_log: List[Dict[str, Any]] = []
    current_spec = spec if isinstance(spec, dict) else {}

    log_event(event_log, "run_started", {"run_id": run_id, "max_iterations": max_iterations})
    write_json(run_root / "spec_initial.json", current_spec)

    overall_success = False
    final_validation_report: Dict[str, Any] = {}
    final_deployment_result: Dict[str, Any] = {}
    completed_iterations = 0

    for iteration_no in range(1, max_iterations + 1):
        completed_iterations = iteration_no
        iteration_root = prepare_iteration_directory(run_root, iteration_no)

        log_event(event_log, "iteration_started", {"iteration_no": iteration_no})
        write_json(iteration_root / "spec_before.json", current_spec)

        # --------------------------------------------------------
        # BUILD PROMPT
        # --------------------------------------------------------
        prompt_result = build_generation_prompt(current_spec)
        write_json(iteration_root / "prompt_result.json", prompt_result)

        if not prompt_result["success"]:
            log_event(
                event_log,
                "prompt_build_failed",
                {
                    "iteration_no": iteration_no,
                    "error_type": prompt_result["error_type"],
                    "error_message": prompt_result["error_message"],
                },
            )
            final_validation_report = _failure_validation_report(
                prompt_result["error_type"],
                prompt_result["error_message"],
            )
            write_json(iteration_root / "validation_report.json", final_validation_report)
            break

        # --------------------------------------------------------
        # GENERATE CODE
        # --------------------------------------------------------
        generation_result = generate_candidate(prompt_result["prompt"])
        write_json(iteration_root / "generation_result.json", generation_result)

        if not generation_result.get("success", False):
            log_event(
                event_log,
                "generation_failed",
                {
                    "iteration_no": iteration_no,
                    "error_type": generation_result.get("error_type"),
                    "error_message": generation_result.get("error_message"),
                },
            )
            final_validation_report = _failure_validation_report(
                generation_result.get("error_type", "generation_failure"),
                generation_result.get("error_message", "Generation failed"),
            )
            write_json(iteration_root / "validation_report.json", final_validation_report)

            current_spec = update_spec_with_failures(current_spec, final_validation_report)
            write_json(iteration_root / "spec_after.json", current_spec)
            continue

        # --------------------------------------------------------
        # WRITE FILES
        # --------------------------------------------------------
        write_result = write_files(generation_result, base_dir=str(repo_root))
        write_json(iteration_root / "write_result.json", write_result)

        if not write_result.get("success", False):
            log_event(
                event_log,
                "write_failed",
                {
                    "iteration_no": iteration_no,
                    "error_type": write_result.get("error_type"),
                    "error_message": write_result.get("error_message"),
                },
            )
            final_validation_report = _failure_validation_report(
                write_result.get("error_type", "file_write_failure"),
                write_result.get("error_message", "File write failed"),
            )
            write_json(iteration_root / "validation_report.json", final_validation_report)

            current_spec = update_spec_with_failures(current_spec, final_validation_report)
            write_json(iteration_root / "spec_after.json", current_spec)
            continue

        # --------------------------------------------------------
        # VALIDATE
        # --------------------------------------------------------
        validation_report = evaluate_app(current_spec, base_dir=str(repo_root))
        final_validation_report = validation_report
        write_json(iteration_root / "validation_report.json", validation_report)

        if not validation_report.get("overall_pass", False):
            log_event(
                event_log,
                "validation_failed",
                {
                    "iteration_no": iteration_no,
                    "finding_count": len(validation_report.get("findings", [])),
                },
            )

            current_spec = update_spec_with_failures(current_spec, validation_report)
            write_json(iteration_root / "spec_after.json", current_spec)
            continue

        # --------------------------------------------------------
        # DEPLOY
        # --------------------------------------------------------
        deployment_result = deploy_system(
            base_dir=str(repo_root),
            validation_report=validation_report,
        )
        final_deployment_result = deployment_result
        write_json(iteration_root / "deployment_result.json", deployment_result)

        if not deployment_result.get("success", False):
            log_event(
                event_log,
                "deployment_failed",
                {
                    "iteration_no": iteration_no,
                    "error_type": deployment_result.get("error_type"),
                    "error_message": deployment_result.get("error_message"),
                },
            )

            failure_report = _failure_validation_report(
                deployment_result.get("error_type", "deployment_failure"),
                deployment_result.get("error_message", "Deployment failed"),
            )
            final_validation_report = merge_validation_reports(validation_report, failure_report)
            write_json(iteration_root / "validation_report_post_deploy.json", final_validation_report)

            current_spec = update_spec_with_failures(current_spec, final_validation_report)
            write_json(iteration_root / "spec_after.json", current_spec)
            continue

        # --------------------------------------------------------
        # SUCCESS
        # --------------------------------------------------------
        overall_success = True
        log_event(
            event_log,
            "iteration_succeeded",
            {
                "iteration_no": iteration_no,
                "live_url": deployment_result.get("live_url"),
            },
        )
        write_json(iteration_root / "spec_after.json", current_spec)
        break

    # ------------------------------------------------------------
    # FINALISE RUN
    # ------------------------------------------------------------
    write_json(run_root / "spec_final.json", current_spec)

    run_summary = {
        "success": overall_success,
        "run_id": run_id,
        "run_root": str(run_root),
        "iterations_completed": completed_iterations,
        "max_iterations": max_iterations,
        "final_validation_report": final_validation_report,
        "final_deployment_result": final_deployment_result,
        "timestamp": now_iso(),
    }

    write_json(run_root / "event_log.json", event_log)
    write_json(run_root / "run_summary.json", run_summary)

    log_event(
        event_log,
        "run_finished",
        {
            "success": overall_success,
            "iterations_completed": completed_iterations,
        },
    )
    write_json(run_root / "event_log.json", event_log)

    return run_summary


def main(spec: Optional[Dict[str, Any]] = None, max_iterations: int = DEFAULT_MAX_ITERATIONS) -> Dict[str, Any]:
    """
    Backward-compatible convenience entrypoint.
    """
    effective_spec = spec if isinstance(spec, dict) else {}
    return run_iteration_loop(effective_spec, max_iterations=max_iterations, base_dir=".")


# ============================================================
# PROMPT + GENERATION WRAPPERS
# ============================================================

def build_generation_prompt(spec: Dict[str, Any]) -> Dict[str, Any]:
    if build_prompt is None:
        return {
            "success": True,
            "prompt": json.dumps(spec, indent=2, ensure_ascii=False),
            "error_type": None,
            "error_message": None,
            "diagnostics": {
                "mode": "fallback_json_prompt",
            },
        }

    try:
        prompt = build_prompt(spec)
        if not isinstance(prompt, str) or not prompt.strip():
            return {
                "success": False,
                "prompt": "",
                "error_type": "prompt_build_failure",
                "error_message": "Prompt builder returned empty prompt",
                "diagnostics": {},
            }

        return {
            "success": True,
            "prompt": prompt,
            "error_type": None,
            "error_message": None,
            "diagnostics": {
                "mode": "prompt_builder",
            },
        }

    except Exception as exc:
        return {
            "success": False,
            "prompt": "",
            "error_type": "prompt_build_failure",
            "error_message": str(exc),
            "diagnostics": {
                "exception_class": exc.__class__.__name__,
                "traceback": traceback.format_exc(),
            },
        }


def generate_candidate(prompt: str) -> Dict[str, Any]:
    if generate_code is None:
        return {
            "success": False,
            "files": [],
            "raw_text": "",
            "provider": "unavailable",
            "model": "unavailable",
            "error_type": "generator_unavailable",
            "error_message": "generate_code could not be imported",
            "diagnostics": {},
        }

    try:
        result = generate_code(prompt)
        if not isinstance(result, dict):
            return {
                "success": False,
                "files": [],
                "raw_text": "",
                "provider": "unknown",
                "model": "unknown",
                "error_type": "generation_failure",
                "error_message": "generate_code returned non-dict result",
                "diagnostics": {},
            }
        return result

    except Exception as exc:
        return {
            "success": False,
            "files": [],
            "raw_text": "",
            "provider": "unknown",
            "model": "unknown",
            "error_type": "generation_failure",
            "error_message": str(exc),
            "diagnostics": {
                "exception_class": exc.__class__.__name__,
                "traceback": traceback.format_exc(),
            },
        }


# ============================================================
# RUN ISOLATION HELPERS
# ============================================================

def generate_run_id() -> str:
    return f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"


def prepare_run_directory(repo_root: Path, run_id: str) -> Path:
    run_root = repo_root / RUNS_DIR_NAME / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "iterations").mkdir(parents=True, exist_ok=True)
    return run_root


def prepare_iteration_directory(run_root: Path, iteration_no: int) -> Path:
    iteration_root = run_root / "iterations" / f"iteration_{iteration_no}"
    iteration_root.mkdir(parents=True, exist_ok=True)
    return iteration_root


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)


def log_event(event_log: List[Dict[str, Any]], event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
    event_log.append(
        {
            "timestamp": now_iso(),
            "event_type": event_type,
            "payload": payload or {},
        }
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# FAILURE / MERGE HELPERS
# ============================================================

def _failure_validation_report(error_type: str, error_message: str) -> Dict[str, Any]:
    finding = {
        "finding_code": error_type,
        "severity": "error",
        "message": error_message,
        "endpoint": {},
        "details": {},
        "actual_value": None,
        "expected_value": None,
    }

    return {
        "overall_pass": False,
        "validation_findings": [finding],
        "findings": [finding],
        "route_coverage_pct": 0.0,
        "declared_endpoints": [],
        "actual_routes": [],
        "summary_json": {
            "overall_pass": False,
            "finding_count": 1,
            "error_count": 1,
            "warning_count": 0,
            "route_coverage_pct": 0.0,
            "declared_route_count": 0,
            "actual_route_count": 0,
        },
    }


def merge_validation_reports(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
    primary_findings = primary.get("findings", []) if isinstance(primary, dict) else []
    secondary_findings = secondary.get("findings", []) if isinstance(secondary, dict) else []

    combined_findings = []
    seen = set()

    for item in primary_findings + secondary_findings:
        if not isinstance(item, dict):
            continue
        key = (
            item.get("finding_code"),
            item.get("severity"),
            item.get("message"),
        )
        if key in seen:
            continue
        seen.add(key)
        combined_findings.append(item)

    overall_pass = not any(item.get("severity") == "error" for item in combined_findings)

    summary_json = {
        "overall_pass": overall_pass,
        "finding_count": len(combined_findings),
        "error_count": sum(1 for item in combined_findings if item.get("severity") == "error"),
        "warning_count": sum(1 for item in combined_findings if item.get("severity") == "warning"),
        "route_coverage_pct": primary.get("route_coverage_pct", 0.0) if isinstance(primary, dict) else 0.0,
        "declared_route_count": len(primary.get("declared_endpoints", [])) if isinstance(primary, dict) else 0,
        "actual_route_count": len(primary.get("actual_routes", [])) if isinstance(primary, dict) else 0,
    }

    return {
        "overall_pass": overall_pass,
        "validation_findings": combined_findings,
        "findings": combined_findings,
        "route_coverage_pct": primary.get("route_coverage_pct", 0.0) if isinstance(primary, dict) else 0.0,
        "declared_endpoints": primary.get("declared_endpoints", []) if isinstance(primary, dict) else [],
        "actual_routes": primary.get("actual_routes", []) if isinstance(primary, dict) else [],
        "summary_json": summary_json,
    }
