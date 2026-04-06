from fastapi import FastAPI
from iteration.controller import run_iteration_loop

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ready"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run():
    # minimal valid spec (required by controller)
    spec = {}

    result = run_iteration_loop(spec)

    return result
