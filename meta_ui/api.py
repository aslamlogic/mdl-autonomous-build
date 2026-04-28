from fastapi import FastAPI, HTTPException
from meta_ui.models import RunCommand, RunResult
import logging, traceback

logger = logging.getLogger(__name__)
app = FastAPI()

def generate(command: RunCommand) -> RunResult:
    instruction = command.instruction
    payload = command.payload
    metadata = command.metadata
return RunResult(status='ok', output={'instruction': command.instruction})

@app.get("/")
async def root():
    return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/run", response_model=RunResult)
async def run_handler(cmd: RunCommand):
    try:
        result = generate(cmd)
        if isinstance(result, dict):
            return RunResult(**result)
        return result
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
