from pathlib import Path
from typing import Any, Dict


class AppBuilder:
    def __init__(self, apps_dir: str = "apps/"):
        self.apps_dir = Path(apps_dir)
        self.apps_dir.mkdir(parents=True, exist_ok=True)

    def build(self, spec: Dict[str, Any]) -> str:
        name = spec.get("name") or "app"
        app_dir = self.apps_dir / name
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "build.txt").write_text(f"Built app: {name}\n", encoding="utf-8")
        return str(app_dir)
