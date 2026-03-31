import json
from pathlib import Path
from typing import Any, Dict, List


class SpecLoader:
    def __init__(self, app_specs_dir: str = "specs/apps/") -> None:
        self.app_specs_dir = Path(app_specs_dir)

    def load_specs(self) -> List[Dict[str, Any]]:
        if not self.app_specs_dir.exists():
            return []
        specs: List[Dict[str, Any]] = []
        for path in sorted(self.app_specs_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as f:
                spec = json.load(f)
            if isinstance(spec, dict):
                spec["__spec_path__"] = str(path)
                specs.append(spec)
        return specs
