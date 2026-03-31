import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class AppSpec:
    name: str
    raw: Dict[str, Any]


class SpecLoader:
    def __init__(self, specs_dir: str = "specs/apps/"):
        self.specs_dir = Path(specs_dir)

    def load(self) -> List[AppSpec]:
        specs: List[AppSpec] = []
        if not self.specs_dir.exists():
            return specs
        for path in sorted(self.specs_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("name") or path.stem
            specs.append(AppSpec(name=name, raw=data))
        return specs
