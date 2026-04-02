from iteration.build import build_system
from iteration.runtime import start_server


def run_iteration_loop(spec: dict):
    print("=== CONTROLLER STARTED ===", flush=True)

    # STEP 1 — Build
    build = build_system(spec)
    print("=== BUILD RESULT ===", build, flush=True)

    # STEP 2 — Runtime
    runtime = start_server()
    print("=== RUNTIME RESULT ===", runtime, flush=True)

    return {
        "build_id": "test_build",
        "message": "Build + runtime executed",
        "deployment_url": "http://localhost:8000",
        "logs": build.get("logs", []) + runtime.get("logs", []),
        "normalized_spec": spec,
    }


if __name__ == "__main__":
    result = run_iteration_loop({})
    print("=== FINAL RESULT ===", result, flush=True)
