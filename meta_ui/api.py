from fastapi import FastAPI
from iteration.controller import controller
from pydantic import BaseModel
app = FastAPI()
class BuildRequest(BaseModel):
    instruction: str
@app.get("/health")
def h(): return {"status":"ok"}
@app.post("/run")
def r(req: BuildRequest): return controller.run(req.instruction)