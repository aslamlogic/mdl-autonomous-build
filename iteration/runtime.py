import subprocess
import time
import requests


def start_server():
    """
    Starts FastAPI server in background and ensures it is reachable.
    """

    process = subprocess.Popen(
        [
            "uvicorn",
            "generated_app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    logs = []

    # Wait for server readiness
    for i in range(10):
        try:
            r = requests.get("http://localhost:8000/health", timeout=2)
            if r.status_code == 200:
                logs.append("Server started successfully")
                return {
                    "status": "running",
                    "process": process,
                    "logs": logs,
                }
        except Exception:
            time.sleep(1)

    # If we reach here → server failed
    process.kill()

    logs.append("Server failed to start")

    return {
        "status": "failed",
        "logs": logs,
    }
