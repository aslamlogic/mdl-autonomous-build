from fastapi.testclient import TestClient
import importlib.util
import sys
from pathlib import Path


def load_generated_app():
    try:
        app_path = Path("generated_app/main.py")

        if not app_path.exists():
            return None, "generated_app/main.py missing"

        spec = importlib.util.spec_from_file_location("generated_app.main", app_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["generated_app.main"] = module
        spec.loader.exec_module(module)

        return module.app, None

    except Exception as e:
        return None, str(e)


def evaluate_system(spec: dict) -> dict:
    app, error = load_generated_app()

    if error:
        return {
            "status": "failure",
            "logs": [f"LOAD_ERROR: {error}"],
            "failing_endpoints": [],
            "schema_mismatches": []
        }

    try:
        client = TestClient(app)

        results = []

        # TEST ROOT
        r = client.get("/")
        results.append(("GET /", r.status_code == 200))

        # TEST HEALTH
        r = client.get("/health")
        results.append(("GET /health", r.status_code == 200))

        failing = [name for name, ok in results if not ok]

        return {
            "status": "success" if not failing else "failure",
            "logs": [],
            "failing_endpoints": failing,
            "schema_mismatches": []
        }

    except Exception as e:
        return {
            "status": "failure",
            "logs": [f"EVAL_ERROR: {str(e)}"],
            "failing_endpoints": [],
            "schema_mismatches": []
        }
