from pathlib import Path
from typing import Any, Dict


class Deployer:
    def __init__(self, apps_dir: str = "apps/") -> None:
        self.apps_dir = Path(apps_dir)

    def deploy(self, build_result: Dict[str, Any]) -> Dict[str, Any]:
        app_name = build_result.get("app", "app")
        deploy_file = self.apps_dir / app_name / "deployed.txt"
        deploy_file.write_text(f"deployed {app_name}\n", encoding="utf-8")
        return {"app": app_name, "deployed": True, "deploy_path": str(deploy_file)}
