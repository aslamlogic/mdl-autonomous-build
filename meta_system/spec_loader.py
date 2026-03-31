from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_app_specs(specs_dir: Path) -> List[Dict[str, Any]]:
    if not specs_dir.exists() or not specs_dir.is_dir():
        return []

    specs: List[Dict[str, Any]] = []
    for path in sorted(specs_dir.glob("**/*")):
        if path.is_file() and path.suffix.lower() in {".json", ".spec", ".txt"}:
            try:
                if path.suffix.lower() == ".json":
                    data = json.loads(path.read_text(encoding="utf-8"))
                else:
                    data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    specs.append(data)
            except Exception:
                continue
    return specs
