#!/usr/bin/env bash
set -euo pipefail

# 1. Unify naming: ensure both api.py and main.py exists and are identical
# This prevents 404s if Render is looking for 'api' and allows 'main' to work.
mkdir -p meta_ui
cp meta_ui/main.py meta_ui/api.py || cp meta_ui/api.py meta_ui/main.py

# 2. Update the requirements to ensure 'uvicorn' and 'fastapi' are locked
cat > requirements.txt <<'REQ'
fastapi
uvicorn
pydantic
