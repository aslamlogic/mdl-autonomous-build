from fastapi import FastAPI
from typing import Dict, Any

from iteration.controller import run_iteration_loop

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ready"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run(spec: Dict[str, Any]):
    """
    Accepts a spec payload and runs the iteration loop.
    """
    result = run_iteration_loop(spec)
    return result
