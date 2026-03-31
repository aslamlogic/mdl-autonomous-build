from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .executor import TaskExecutor


class EngineBuilder:
    def __init__(self, executor: TaskExecutor) -> None:
        self.executor = executor

    def build_engine(self, spec: Dict[str, Any], app_dir: Path) -> Dict[str, Any]:
        app_dir.mkdir(parents=True, exist_ok=True)
        engine_file = app_dir / "engine.json"
        payload = {"app": spec.get("name", "unknown"), "engine": spec.get("engine", "default")}
        engine_file.write_text(__import__("json").dumps(payload, indent=2), encoding="utf-8")
        return {"engine_file": str(engine_file), "status": "built"}
