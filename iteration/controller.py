def run_iteration_loop(spec: dict):
    print("=== CONTROLLER STARTED ===")

    return {
        "build_id": "test_build",
        "message": "Controller executed",
        "deployment_url": "http://localhost:8000",
        "logs": ["Controller ran successfully"],
        "normalized_spec": spec,
    }


if __name__ == "__main__":
    # test run
    result = run_iteration_loop({})
    print(result)
