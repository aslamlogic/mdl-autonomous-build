from fastapi import FastAPI
from typing import Any

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/runs")
def runs():
    return {"status": "ready"}


@app.post("/run")
def run_system() -> Any:
    try:
        # Lazy import to avoid breaking API boot
        from iteration.controller import main

        result = main()

        return {
            "status": "executed",
            "result": result
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
