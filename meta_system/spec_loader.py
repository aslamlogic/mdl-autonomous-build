"""Load application specifications for the meta system."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class AppSpec:
    name: str
    raw: Dict[str, Any]
    path: Path


class SpecLoader:
    def __init__(self, app_specs_dir: str = "specs/apps/") -> None:
        self.app_specs_dir = Path(app_specs_dir)

    def load(self) -> List[AppSpec]:
        if not self.app_specs_dir.exists():
            return []

        specs: List[AppSpec] = []
        for path in sorted(self.app_specs_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            name = raw.get("name") or path.stem
            specs.append(AppSpec(name=name, raw=raw, path=path))
        return specs
