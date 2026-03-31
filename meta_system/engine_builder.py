from pathlib import Path
from typing import Any, Dict


class EngineBuilder:
    def __init__(self, meta_dir: str = "meta_system/"):
        self.meta_dir = Path(meta_dir)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def build(self, spec: Dict[str, Any]) -> str:
        name = spec.get("name") or "engine"
        engine_dir = self.meta_dir / "engines" / name
        engine_dir.mkdir(parents=True, exist_ok=True)
        (engine_dir / "engine.txt").write_text(f"Engine prepared for: {name}\n", encoding="utf-8")
        return str(engine_dir)
