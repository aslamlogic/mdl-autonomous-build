from iteration.build import build_system


def run_iteration_loop(spec: dict):
    print("=== CONTROLLER STARTED ===")

    result = build_system(spec)

    print("=== BUILD RESULT ===")
    print(result)

    return {
        "build_id": "test_build",
        "message": "Build executed",
        "deployment_url": "http://localhost:8000",
        "logs": result.get("logs", []),
        "normalized_spec": spec,
    }


if __name__ == "__main__":
    run_iteration_loop({})
