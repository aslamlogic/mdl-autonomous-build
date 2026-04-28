
from .models import RunCommand, RunResult
@app.post("/run", response_model=RunResult)
async def run_handler(cmd: RunCommand):
    # Industrial Grade: Explicit Model Passing
    return generate(cmd.instruction, cmd.payload, cmd.metadata)

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import os, sys

from iteration.controller import controller

app = FastAPI(title="MDL Autonomous Factory")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent.parent / "static"

class RunRequest(BaseModel):
    instruction: str
    spec: Optional[dict] = None

@app.get("/")
def ui_root():
    idx = STATIC_DIR / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    return {"status": "ok", "ui": "missing static/index.html"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/diag")
def diag():
    return {
        "python": sys.version,
        "openai_api_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }

@app.post("/run")
def run(req: RunRequest):
    try:
        result = controller.run(req.instruction)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(status_code=500, content={"status": "error", **result})
        return {"status": "success", "result": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
