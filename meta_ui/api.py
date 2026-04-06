"""
Meta UI API

Exposes HTTP endpoints for interacting with the Meta system.

Routes:
- /health → basic health check
- /run → triggers iteration loop
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Import controller
from iteration.controller import run_iteration_loop


app = FastAPI()


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------
# RUN SYSTEM
# --------------------------------------------------

@app.post("/run")
def run():
    try:
        result = run_iteration_loop()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e)
            },
            status_code=500
        )


# --------------------------------------------------
# ROOT (optional, prevents 405 confusion)
# --------------------------------------------------

@app.get("/")
def root():
    return {"status": "ready"}
