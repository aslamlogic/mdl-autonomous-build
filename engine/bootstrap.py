# ONLY SHOWING THE CHANGED PART INSIDE validate_files()

def validate_files(payload: dict, spec: dict) -> None:
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        fail("Validation failed: no files returned")

    by_path: dict[str, str] = {}

    for item in files:
        path = item.get("path")
        content = item.get("content")

        validate_path(path)
        by_path[path] = normalise_content(content)

    main_py = by_path["main.py"]
    requirements_txt = by_path["requirements.txt"].lower()

    endpoints = spec.get("api", {}).get("endpoints", [])

    for endpoint in endpoints:
        method = str(endpoint.get("method", "")).lower()
        path = endpoint.get("path")

        if not method or not path:
            fail("Validation failed: endpoint missing method or path")

        # FLEXIBLE MATCH (KEY FIX)
        pattern = rf"@app\.{method}\s*\(\s*[\"']{path}[\"']"
        if not re.search(pattern, main_py):
            fail(f"Validation failed: endpoint missing {method.upper()} {path}")
