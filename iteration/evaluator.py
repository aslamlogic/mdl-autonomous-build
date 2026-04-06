# iteration/evaluator.py

from fastapi.testclient import TestClient


def evaluate_system(app, spec):
    """
    Deterministic evaluator for generated FastAPI app.
    No httpx usage. No 'app=' argument misuse.
    """

    result = {
        "status": "failure",
        "logs": [],
        "failing_endpoints": [],
        "schema_mismatches": []
    }

    try:
        # CORRECT client
        client = TestClient(app)

        # --- Health check ---
        response = client.get("/health")

        if response.status_code != 200:
            result["logs"].append(f"Health check failed: {response.status_code}")
            return result

        try:
            data = response.json()
        except Exception:
            result["logs"].append("Health endpoint did not return JSON")
            return result

        if data.get("status") != "ok":
            result["logs"].append("Health endpoint returned invalid payload")
            return result

        # --- Passed ---
        result["status"] = "success"
        return result

    except Exception as e:
        result["logs"].append(f"EVAL_ERROR: {str(e)}")
        return result
