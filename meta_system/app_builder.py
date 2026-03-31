"""Build application artifacts from specs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class AppBuilder:
    def __init__(self, apps_dir: str = "apps/") -> None:
        self.apps_dir = Path(apps_dir)

    def build(self, app_spec: Dict[str, Any]) -> Path:
        name = app_spec.get("name", "app")
        app_dir = self.apps_dir / name
        app_dir.mkdir(parents=True, exist_ok=True)
        artifact = app_dir / "app.py"
        artifact.write_text(
            f"# Auto-generated app: {name}\n"
            f"SPEC = {app_spec!r}\n",
            encoding="utf-8",
        )
        return artifact
