from fastapi import FastAPI
from pydantic import BaseModel
import traceback

from iteration.controller import run_iteration_loop

app = FastAPI()


class RunRequest(BaseModel):
    objective: str
    constraints: list[str]
    targets: list[str]
    iteration_mode: str
    termination_condition: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run(req: RunRequest):
    try:
        result = run_iteration_loop(
            objective=req.objective,
            constraints=req.constraints,
            targets=req.targets,
            iteration_mode=req.iteration_mode,
            termination_condition=req.termination_condition
        )
        return {"status": "completed", "result": result}
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }
