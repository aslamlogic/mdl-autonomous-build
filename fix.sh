#!/bin/bash
mkdir -p meta_ui engine
cat << 'PY' > meta_ui/api.py
from fastapi import FastAPI, UploadFile, File, Request; from fastapi.middleware.cors import CORSMiddleware; import os, base64, requests, threading
app = FastAPI(); app.add_middleware(CORSMiddleware, allow_origins=["*"])
@app.get("/health")
async def h(): return {"status":"ok","controller":True}
@app.post("/upload-spec")
async def u(file: UploadFile = File(...)):
    c = await file.read(); b = base64.b64encode(c).decode()
    r = requests.put(f"https://api.github.com/repos/{os.getenv('GITHUB_REPO')}/contents/specs/{file.filename}", headers={"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"}, json={"message": "upload spec", "content": b})
    return {"status": r.status_code}
@app.post("/run")
async def r(req: Request): return {"status":"accepted"}
PY
cat << 'PY' > engine/llm_interface.py
def generate(i, **k): return {"status":"stub"}
PY
for p in openai fastapi uvicorn requests pydantic python-multipart; do grep -q "$p" requirements.txt || echo "$p" >> requirements.txt; done
git add . && git commit -m "chore: factory wiring" && git push origin $(git rev-parse --abbrev-ref HEAD)
