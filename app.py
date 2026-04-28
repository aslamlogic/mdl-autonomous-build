# Top-level entrypoint for Render/auto-detect systems.
# Re-export the FastAPI 'app' object from the meta_ui package.
try:
    from meta_ui.main import app  # preferred canonical module
except Exception:
    # fallback: try api.py
    try:
        from meta_ui.api import app
    except Exception:
        raise

# Export for WSGI/ASGI servers that look for 'app' in root
__all__ = ["app"]
