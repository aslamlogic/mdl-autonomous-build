from fastapi import FastAPI
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
