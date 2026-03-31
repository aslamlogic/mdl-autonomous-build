from pathlib import Path
from typing import Any, Dict


class EngineBuilder:
    def __init__(self, apps_dir: str = "apps/") -> None:
        self.apps_dir = Path(apps_dir)

    def build(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        app_name = spec.get("name") or spec.get("app_name") or "app"
        app_dir = self.apps_dir / app_name
        app_dir.mkdir(parents=True, exist_ok=True)
        engine_file = app_dir / "engine.txt"
        engine_file.write_text(f"engine built for {app_name}\n", encoding="utf-8")
        return {"app": app_name, "engine_path": str(engine_file)}
