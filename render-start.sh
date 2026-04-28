#!/usr/bin/env bash
# Explicit start command wrapper for Render
set -euo pipefail
echo "[render-start] starting uvicorn meta_ui.main:app on $PORT"
exec python -m uvicorn meta_ui.main:app --host 0.0.0.0 --port ${PORT:-8000}
