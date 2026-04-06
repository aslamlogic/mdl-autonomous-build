from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
import os
from typing import Any

app = FastAPI()


@app.get("/")
def root():
    return FileResponse("meta_ui/static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/runs")
def runs():
    return {"status": "ready"}


@app.get("/env")
def env():
    return {
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "log_level": os.getenv("LOG_LEVEL", "unknown")
    }


@app.post("/runs")
def run_system():
    try:
        from iteration.controller import run_iteration_loop, load_spec
        result = run_iteration_loop(load_spec())
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )
