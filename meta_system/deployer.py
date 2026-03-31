"""Deploy built applications."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List


class Deployer:
    def __init__(self, deploy_root: str = "apps/") -> None:
        self.deploy_root = Path(deploy_root)

    def deploy(self, artifacts: Iterable[Path]) -> List[str]:
        deployed: List[str] = []
        for artifact in artifacts:
            deployed.append(str(artifact))
        return deployed
