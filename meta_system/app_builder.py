from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .executor import TaskExecutor
from .engine_builder import EngineBuilder


class AppBuilder:
    def __init__(self, executor: TaskExecutor, engine_builder: EngineBuilder, apps_dir: Path) -> None:
        self.executor = executor
        self.engine_builder = engine_builder
        self.apps_dir = apps_dir

    def build(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        app_name = spec.get("name", "unnamed_app")
        app_dir = self.apps_dir / app_name
        app_dir.mkdir(parents=True, exist_ok=True)
        build_file = app_dir / "build.json"
        engine_result = self.engine_builder.build_engine(spec, app_dir)
        build_payload = {"app": app_name, "spec": spec, "engine": engine_result}
        build_file.write_text(json.dumps(build_payload, indent=2), encoding="utf-8")
        return {"build_file": str(build_file), "app_dir": str(app_dir), "status": "built", "engine": engine_result}
