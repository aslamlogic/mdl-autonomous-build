#!/usr/bin/env python3
"""
capture_sink.py

Simple, audit-friendly capture sink for errors and solutions.
- Appends JSON lines to ./logs/errors.log and ./logs/solutions.log
- Provides a "run" subcommand to execute a command and log failures automatically.
- Zero external dependencies.
"""
import argparse
import json
import os
import sys
import uuid
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

LOG_DIR = os.environ.get("CAPTURE_SINK_LOG_DIR", "logs")
ERRORS_FILE = os.path.join(LOG_DIR, "errors.log")
SOLUTIONS_FILE = os.path.join(LOG_DIR, "solutions.log")


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def atomic_append(path: str, obj: Dict[str, Any]):
    line = json.dumps(obj, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass


def base_context() -> Dict[str, Any]:
    host = None
    try:
        import socket
        host = socket.gethostname()
    except Exception:
        host = os.environ.get("HOSTNAME")
    return {
        "timestamp": now_iso(),
        "host": host,
        "env_commit": os.environ.get("GIT_COMMIT") or os.environ.get("COMMIT_SHA"),
        "env_render_build": os.environ.get("RENDER_BUILD_ID"),
        "env_owner": os.environ.get("RENDER_OWNER_ID"),
        "invoked_by": os.environ.get("USER") or os.environ.get("USERNAME"),
        "capture_sink_version": "1.0",
    }


def record_error(
    component: str,
    message: str,
    stacktrace: Optional[str] = None,
    run_command: Optional[Dict[str, Any]] = None,
    severity: str = "medium",
    sample_input: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    ensure_log_dir()
    incident_id = str(uuid.uuid4())
    entry = {
        "incident_id": incident_id,
        "component": component,
        "message": message,
        "stacktrace": stacktrace,
        "run_command": run_command,
        "severity": severity,
        "sample_input": sample_input,
        "processed": False,
        **base_context(),
    }
    if extra:
        entry["extra"] = extra
    atomic_append(ERRORS_FILE, entry)
    print(incident_id)
    return incident_id


def record_solution(
    incident_ids: List[str],
    branch: Optional[str],
    pr_url: Optional[str],
    patch_summary: str,
    test_results: Optional[Dict[str, Any]] = None,
    author: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    ensure_log_dir()
    solution_id = str(uuid.uuid4())
    entry = {
        "solution_id": solution_id,
        "incident_ids": incident_ids,
        "branch": branch,
        "pr_url": pr_url,
        "patch_summary": patch_summary,
        "test_results": test_results,
        "author": author or os.environ.get("USER") or os.environ.get("USERNAME"),
        "recorded_at": now_iso(),
        **base_context(),
    }
    if extra:
        entry["extra"] = extra
    atomic_append(SOLUTIONS_FILE, entry)
    print(solution_id)
    return solution_id


def run_and_capture(cmd: List[str], component: str, severity: str):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate()
    exit_code = proc.returncode
    if exit_code == 0:
        if stdout:
            print(stdout, end="")
        return 0
    else:
        message = f"Command exited with {exit_code}: {' '.join(cmd)}"
        stacktrace = stderr if stderr else stdout
        run_command = {"cmd": cmd, "exit_code": exit_code}
        incident_id = record_error(
            component=component,
            message=message,
            stacktrace=stacktrace,
            run_command=run_command,
            severity=severity,
        )
        sys.stderr.write(stderr if stderr else stdout)
        return exit_code


def main():
    parser = argparse.ArgumentParser(description="Capture sink for errors and solutions (single file).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_err = sub.add_parser("error", help="Record an error/incident")
    p_err.add_argument("--component", required=True)
    p_err.add_argument("--message", required=True)
    p_err.add_argument("--stacktrace-file", help="Path to a file containing stacktrace (optional)")
    p_err.add_argument("--severity", choices=["low", "medium", "high", "critical"], default="medium")
    p_err.add_argument("--run-command-json", help="JSON string describing the run command/input")
    p_err.add_argument("--sample-input-json", help="JSON string of a sample input")
    p_err.add_argument("--extra-json", help="Extra JSON to attach")

    p_sol = sub.add_parser("solution", help="Record a solution/fix")
    p_sol.add_argument("--incident-ids", required=True, help="Comma-separated incident IDs this solution addresses")
    p_sol.add_argument("--branch", help="Branch name where fix lives")
    p_sol.add_argument("--pr-url", help="PR URL (if created)")
    p_sol.add_argument("--patch-summary", required=True, help="Short summary of the patch / fix")
    p_sol.add_argument("--test-results-json", help="JSON string of test results")
    p_sol.add_argument("--author", help="Author name")
    p_sol.add_argument("--extra-json", help="Extra JSON to attach")

    p_run = sub.add_parser("run", help="Run a command; log failure as an error automatically")
    p_run.add_argument("--component", required=True)
    p_run.add_argument("--severity", choices=["low", "medium", "high", "critical"], default="medium")
    p_run.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to execute (prepend with -- if necessary)")

    args = parser.parse_args()

    if args.cmd == "error":
        stacktrace = None
        if args.stacktrace_file:
            try:
                with open(args.stacktrace_file, "r", encoding="utf-8") as f:
                    stacktrace = f.read()
            except Exception as e:
                stacktrace = f"Failed to read stacktrace file: {e}"
        run_command = None
        sample_input = None
        extra = None
        if args.run_command_json:
            try:
                run_command = json.loads(args.run_command_json)
            except Exception as e:
                run_command = {"_parse_error": str(e), "raw": args.run_command_json}
        if args.sample_input_json:
            try:
                sample_input = json.loads(args.sample_input_json)
            except Exception as e:
                sample_input = {"_parse_error": str(e), "raw": args.sample_input_json}
        if args.extra_json:
            try:
                extra = json.loads(args.extra_json)
            except Exception as e:
                extra = {"_parse_error": str(e), "raw": args.extra_json}
        record_error(
            component=args.component,
            message=args.message,
            stacktrace=stacktrace,
            run_command=run_command,
            severity=args.severity,
            sample_input=sample_input,
            extra=extra,
        )

    elif args.cmd == "solution":
        try:
            incident_ids = [i.strip() for i in args.incident_ids.split(",") if i.strip()]
        except Exception:
            incident_ids = []
        test_results = None
        extra = None
        if args.test_results_json:
            try:
                test_results = json.loads(args.test_results_json)
            except Exception as e:
                test_results = {"_parse_error": str(e), "raw": args.test_results_json}
        if args.extra_json:
            try:
                extra = json.loads(args.extra_json)
            except Exception as e:
                extra = {"_parse_error": str(e), "raw": args.extra_json}
        record_solution(
            incident_ids=incident_ids,
            branch=args.branch,
            pr_url=args.pr_url,
            patch_summary=args.patch_summary,
            test_results=test_results,
            author=args.author,
            extra=extra,
        )

    elif args.cmd == "run":
        # argparse REMAINDER is stored in args.cmdlist in some versions; retrieve from sys.argv fallback
        cmdlist = args.cmd if isinstance(args.cmd, list) else []
        # actual remainder may be in sys.argv after '--'; reconstruct
        remainder = []
        argv = sys.argv[1:]
        if "--" in argv:
            idx = argv.index("--")
            remainder = argv[idx+1:]
        else:
            # fallback: find first token that is not the --component/--severity options and treat rest as cmd
            # keep simple: use argparse.REMAINDER via args
            remainder = []
        # prefer argparse.REMAINDER parsed tokens
        if getattr(args, 'cmd', None):
            # when using argparse.REMAINDER, args.cmd is the list of tokens
            try:
                remainder = args.cmd if isinstance(args.cmd, list) else remainder
            except Exception:
                pass
        if remainder and remainder[0] == "--":
            remainder = remainder[1:]
        if not remainder:
            print("No command provided. Usage: capture_sink.py run --component X -- <command...>")
            sys.exit(2)
        exit_code = run_and_capture(remainder, component=args.component, severity=args.severity)
        sys.exit(exit_code)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
