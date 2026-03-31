from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .executor import TaskExecutor


class Deployer:
    def __init__(self, executor: TaskExecutor, apps_dir: Path) -> None:
        self.executor = executor
        self.apps_dir = apps_dir

    def deploy(self, spec: Dict[str, Any], app_result: Dict[str, Any]) -> Dict[str, Any]:
        app_name = spec.get("name", "unnamed_app")
        app_dir = Path(app_result.get("app_dir", self.apps_dir / app_name))
        deploy_file = app_dir / "deploy.json"
        payload = {"app": app_name, "deployed": True, "source": app_result}
        deploy_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"deploy_file": str(deploy_file), "status": "deployed"}
