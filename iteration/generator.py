import types

# ============================================================
# TEMPORARY DETERMINISTIC GENERATOR (STABLE BASELINE)
# ============================================================

def generate_code(prompt: str):
    """
    Deterministic fallback generator.

    This guarantees:
    - Valid FastAPI app
    - Correct /health endpoint
    - System convergence

    You can later replace this with real LLM call.
    """

    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
