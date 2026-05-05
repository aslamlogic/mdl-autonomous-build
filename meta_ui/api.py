from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from iteration.controller import controller
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

app = FastAPI(title="MDL Autonomous Build System - SST v2.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

class BuildRequest(BaseModel):
    instruction: str
    spec: Optional[dict] = None

@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>MDL Autonomous Software Factory – SST v2.2</h1><p>Root UI is now active.</p>")

@app.get("/health")
def health():
    return {"status": "ok", "version": "SST v2.2", "smr": "v5.6"}

@app.post("/run")
def run_build(request: BuildRequest):
    try:
        result = controller.run(request.instruction)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
