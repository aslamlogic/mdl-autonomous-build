def update_spec(spec, evaluation):
    new_spec = {"endpoints": []}

    for ep in spec.get("endpoints", []):
        method = ep.get("method", "")
        path = ep.get("path", "")

        # Fix invalid methods
        if isinstance(method, str):
            method = method.upper()

        # Basic fallback
        if method not in {"GET", "POST", "PUT", "DELETE"}:
            method = "GET"

        if not path.startswith("/"):
            path = f"/{path}"

        new_spec["endpoints"].append({
            "method": method,
            "path": path
        })

    return new_spec
