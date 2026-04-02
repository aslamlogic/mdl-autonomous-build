from fastapi import FastAPI
from pydantic import BaseModel
from iteration.controller import run_iteration_loop

app = FastAPI()

class SpecRequest(BaseModel):
    spec: dict


@app.post("/generate")
def generate_system(request: SpecRequest):
    try:
        result = run_iteration_loop(request.spec)

        return {
            "ok": True,
            "build_id": result.get("build_id", "local_build"),
            "message": "Build completed",
            "deployment_url": result.get("deployment_url"),
            "logs": result.get("logs", [])
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }
