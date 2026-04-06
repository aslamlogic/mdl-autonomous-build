import sys
import json
from pathlib import Path

# =========================
# FORCE CORRECT EVALUATOR LOAD
# =========================
sys.modules.pop("iteration.evaluator", None)

import iteration.evaluator as evaluator
evaluate_system = evaluator.evaluate_system


# =========================
# GENERATOR (embedded)
# =========================

GENERATED_APP_DIR = Path("generated_app")
MAIN_FILE = GENERATED_APP_DIR / "main.py"


def generate_app(spec: dict) -> dict:
    try:
        GENERATED_APP_DIR.mkdir(parents=True, exist_ok=True)

        code = build_main_py(spec)

        with open(MAIN_FILE, "w") as f:
            f.write(code)

        return {
            "status": "success",
            "generated_files": [str(MAIN_FILE)]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def build_main_py(spec: dict) -> str:
    return '''from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"status": "generated_app_running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/echo")
def echo(payload: dict):
    return {"received": payload}
'''


# =========================
# CONTROLLER ENTRY POINT
# =========================

def run_iteration_loop(spec: dict):
    iterations = []

    for i in range(1, 2):  # single iteration

        # STEP 1: GENERATE
        generation_result = generate_app(spec)

        if generation_result["status"] != "success":
            return {
                "status": "failed",
                "stage": "generation",
                "error": generation_result
            }

        # STEP 2: EVALUATE
        evaluation = evaluate_system(spec)

        iterations.append({
            "iteration": i,
            "status": "failed" if evaluation.get("status") != "success" else "success",
            "evaluation": evaluation
        })

    return {
        "status": "started",
        "iterations": iterations
    }
