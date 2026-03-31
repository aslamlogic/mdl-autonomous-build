"""Build shared engine/bootstrap artifacts."""

from __future__ import annotations

from pathlib import Path


class EngineBuilder:
    def __init__(self, output_dir: str = "meta_system/") -> None:
        self.output_dir = Path(output_dir)

    def build(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        engine_path = self.output_dir / "engine.py"
        engine_path.write_text(
            """# Auto-generated engine bootstrap\n\n"""
            "def bootstrap():\n"
            "    return {'status': 'ok'}\n",
            encoding="utf-8",
        )
        return engine_path
