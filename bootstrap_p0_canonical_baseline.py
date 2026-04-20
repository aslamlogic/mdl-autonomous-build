import os
import subprocess
from pathlib import Path
from datetime import datetime

BASE = Path(".")

def write_file(path: str, content: str) -> None:
    full_path = BASE / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"[P0] CREATED: {path}")

print("=== P0 CANONICAL BASELINE ESTABLISHMENT ===")

# P0.1 Declare canonical authority
write_file("CANONICAL_AUTHORITY.marker", f"""
CANONICAL BUILD AUTHORITY ESTABLISHED
Date: {datetime.utcnow().isoformat()}Z
Authority: Formal Technical Specification for Autonomous SW Factory
Specimen: Current mdl-autonomous-build repo (forensic only)
""")

# P0.2 Remove duplicate workflows
print("[P0] Removing duplicate workflow files...")
for wf in ["run-meta.yml", "build-and-deploy.yml"]:
    p = BASE / ".github" / "workflows" / wf
    if p.exists():
        p.unlink()
        print(f"[P0] REMOVED duplicate workflow: {wf}")

# P0.3 Repair broken meta_ui/api.py (full canonical replacement)
api_content = '''from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from iteration.controller import IterationController


app = FastAPI()


class RunRequest(BaseModel):
    instruction: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "MDL Autonomous Build API"}


@app.post("/run")
def run_build(request: RunRequest):
    """Canonical /run endpoint aligned to P1–P12 pipeline."""
    controller = IterationController()
    result = controller.run(
        workspace_path=".",
        initial_spec_text=request.instruction or "Build a minimal FastAPI health endpoint",
        run_id="run_001"
    )
    return result
'''
write_file("meta_ui/api.py", api_content)

# P0.4 Generate initial failure corpus from specimen
write_file("forensic/failure_corpus.json", '''{
  "corpus_version": "1.0",
  "generated_at": "''' + datetime.utcnow().isoformat() + '''Z",
  "specimen_defects": [
    {"ku_id": "KU-19", "failure_class": "boundary_failure", "description": "meta_ui/api.py syntactically broken"},
    {"ku_id": "KU-20", "failure_class": "workflow_conflict", "description": "Multiple active GitHub workflows present"},
    {"ku_id": "KU-18", "failure_class": "orchestration_failure", "description": "Validators present but not wired into unified P6 chain"}
  ],
  "status": "ready_for_p6_injection"
}
''')

# P0.5 Create salvage register
write_file("forensic/salvage_register.json", '''{
  "salvage_candidates": [
    "engine/llm_interface.py",
    "iteration/deploy.py",
    "projects/registry.py"
  ],
  "quarantined_modules": [],
  "note": "Only interface-conformant components may be reused in canonical build"
}
''')

print("=== P0 CANONICAL BASELINE COMPLETE ===")
print("Next step: git add . && git commit -m \"P0: Canonical baseline established\" && git push")
print("After push and Render redeploy, reply exactly: P0 COMPLETE")
