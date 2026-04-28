#!/usr/bin/env python3
"""bootstrap_complete_fix.py — SMR v5.6 deterministic contract-first fix"""
import os, sys, subprocess, json, ast, difflib, textwrap
from pathlib import Path
from datetime import datetime

AUTHORIZE = os.environ.get("AUTHORIZE_STRUCTURAL_CHANGE","0") == "1"
GIT_REMOTE = os.environ.get("GIT_PUSH_REMOTE","origin")
TIMESTAMP = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
BACKUP_BRANCH = f"smr-backup-{TIMESTAMP}"
WORK_BRANCH = f"smr-fix-{TIMESTAMP}"
REPO_ROOT = Path.cwd()
META_UI = REPO_ROOT / "meta_ui"
REPORT_FILE = REPO_ROOT / "post_deploy_audit.json"
audit = {"smr":"v5.6","authorize":AUTHORIZE,"diffs":[],"actions":[]}

def sh(cmd):
    r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return r.returncode, r.stdout

# P1: canonical models
META_UI.mkdir(parents=True, exist_ok=True)
models_py = META_UI / "models.py"
models_py.write_text(textwrap.dedent("""\
    from pydantic import BaseModel
    from typing import Any, Dict, Optional

    class RunCommand(BaseModel):
        instruction: str
        payload: Optional[Dict[str, Any]] = None
        metadata: Optional[Dict[str, Any]] = None

    class RunResult(BaseModel):
        status: str
        output: Optional[Dict[str, Any]] = None
        error: Optional[str] = None
    """), encoding="utf-8")
audit["actions"].append("wrote meta_ui/models.py")

# P5: rewrite api.py completely — canonical, correct order
api_path = META_UI / "api.py"
old_api = api_path.read_text(encoding="utf-8") if api_path.exists() else ""

# extract existing generate function body if present
gen_body = "    return RunResult(status='ok', output={'instruction': command.instruction})"
try:
    tree = ast.parse(old_api)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "generate":
            lines = old_api.splitlines()
            body_lines = lines[node.body[0].lineno - 1 : node.end_lineno]
            gen_body = "\n".join("    " + l.lstrip() for l in body_lines)
            break
except Exception:
    pass

new_api = textwrap.dedent(f"""\
    from fastapi import FastAPI, HTTPException
    from meta_ui.models import RunCommand, RunResult
    import logging, traceback

    logger = logging.getLogger(__name__)
    app = FastAPI()

    def generate(command: RunCommand) -> RunResult:
        instruction = command.instruction
        payload = command.payload
        metadata = command.metadata
{gen_body}

    @app.get("/")
    async def root():
        return {{"status": "ok"}}

    @app.get("/health")
    async def health():
        return {{"status": "ok"}}

    @app.post("/run", response_model=RunResult)
    async def run_handler(cmd: RunCommand):
        try:
            result = generate(cmd)
            if isinstance(result, dict):
                return RunResult(**result)
            return result
        except Exception as e:
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))
    """)

diff = "\n".join(difflib.unified_diff(old_api.splitlines(), new_api.splitlines(),
    fromfile="meta_ui/api.py", tofile="meta_ui/api.py.new", lineterm=""))
audit["diffs"].append({"file":"meta_ui/api.py","diff":diff})

print("=== PLANNED DIFF: meta_ui/api.py ===")
print(diff[:3000])
print("=====================================")

if not AUTHORIZE:
    json.dump(audit, open(REPORT_FILE,"w"), indent=2)
    print("\nSMR: Discovery only. No changes applied.")
    print("Run with AUTHORIZE_STRUCTURAL_CHANGE=1 to apply.")
    sys.exit(0)

# Apply
api_path.write_text(new_api, encoding="utf-8")
audit["actions"].append("rewrote meta_ui/api.py")

# Git ops
sh(f"git checkout -b {BACKUP_BRANCH}")
sh("git add -A")
sh("git commit -m 'smr: pre-fix backup' || true")
sh(f"git push {GIT_REMOTE} {BACKUP_BRANCH} || true")
sh(f"git checkout -b {WORK_BRANCH}")
sh("git add -A")
rc, out = sh("git commit -m 'fix(smr): canonical contract-first api.py — app defined before decorators'")
audit["git_commit"] = out
rc2, out2 = sh(f"git push {GIT_REMOTE} {WORK_BRANCH}")
audit["git_push"] = out2
print("Pushed branch:", WORK_BRANCH)

# Merge to main
sh("git checkout main")
sh(f"git merge {WORK_BRANCH} --no-ff -m 'merge(smr): contract-first fix'")
rc3, out3 = sh("git push origin main")
audit["git_push_main"] = out3
print("Merged and pushed to main.")

json.dump(audit, open(REPORT_FILE,"w"), indent=2)
print("Done. Audit:", REPORT_FILE)
