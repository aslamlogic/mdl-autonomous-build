from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from iteration.controller import controller
import uvicorn
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="MDL Autonomous Build System - SMR v5.6 Fixed")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BuildRequest(BaseModel):
    instruction: str
    spec: Optional[dict] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/run")
def run_build(request: BuildRequest):
    print("Received build request")
    try:
        result = controller.run(request.instruction)
        return {
            "status": "success",
            "result": result,
            "message": "Build completed under SMR v5.6"
        }
    except Exception as e:
        print(f"Error in /run: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("meta_ui.api:app", host="0.0.0.0", port=10000, reload=False)
