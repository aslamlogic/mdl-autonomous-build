from fastapi import FastAPI, Request
from iteration.controller import run_iteration_loop

app = FastAPI()


@app.get("/")
def root():
    return {"status": "meta_dev_launcher_running"}


@app.post("/run")
async def run(request: Request):
    try:
        spec = await request.json()

        print("[DEBUG SPEC RECEIVED]", spec)

        result = run_iteration_loop(spec)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
