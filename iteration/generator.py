from pathlib import Path


GENERATED_APP_DIR = Path("generated_app")
MAIN_FILE = GENERATED_APP_DIR / "main.py"


def generate_app(spec: dict) -> dict:
    try:
        print("[GENERATOR] Starting generation")

        GENERATED_APP_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[GENERATOR] Ensured directory exists: {GENERATED_APP_DIR}")

        code = build_main_py(spec)
        print("[GENERATOR] Code built")

        with open(MAIN_FILE, "w") as f:
            f.write(code)

        print(f"[GENERATOR] Wrote file: {MAIN_FILE.resolve()}")

        return {
            "status": "success",
            "generated_files": [str(MAIN_FILE.resolve())]
        }

    except Exception as e:
        print(f"[GENERATOR] ERROR: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }


def build_main_py(spec: dict) -> str:
    # FIXED BASELINE APP — DO NOT IMPLEMENT SPEC
    return '''
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "generated_app_running"}

@app.get("/health")
def health():
    return {"status": "ok"}
'''
