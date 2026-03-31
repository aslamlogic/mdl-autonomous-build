from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="meta-dev", version="14")


@app.get("/")
def root():
    return {"project": "meta-dev", "version": "14", "status": "ok"}


@app.get("/health")
def health():
    return JSONResponse({"status": "healthy"})
