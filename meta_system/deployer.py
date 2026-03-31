from pathlib import Path
from typing import Any, Dict


class Deployer:
    def deploy(self, app_path: str, spec: Dict[str, Any]) -> str:
        deploy_dir = Path(app_path) / "deployed"
        deploy_dir.mkdir(parents=True, exist_ok=True)
        (deploy_dir / "deploy.txt").write_text(
            f"Deployed {spec.get('name', 'app')} from {app_path}\n",
            encoding="utf-8",
        )
        return str(deploy_dir)
