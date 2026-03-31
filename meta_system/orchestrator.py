"""Meta system orchestrator."""

from __future__ import annotations

from dataclasses import asdict
from typing import List

from meta_system.app_builder import AppBuilder
from meta_system.deployer import Deployer
from meta_system.engine_builder import EngineBuilder
from meta_system.executor import Executor
from meta_system.spec_loader import SpecLoader


class Orchestrator:
    def __init__(
        self,
        app_specs_dir: str = "specs/apps/",
        meta_system_dir: str = "meta_system/",
        apps_dir: str = "apps/",
        max_workers: int | None = None,
    ) -> None:
        self.loader = SpecLoader(app_specs_dir=app_specs_dir)
        self.engine_builder = EngineBuilder(output_dir=meta_system_dir)
        self.app_builder = AppBuilder(apps_dir=apps_dir)
        self.deployer = Deployer(deploy_root=apps_dir)
        self.executor = Executor(max_workers=max_workers)

    def run(self) -> dict:
        self.engine_builder.build()
        specs = self.loader.load()
        artifacts = self.executor.map_parallel(
            lambda spec: self.app_builder.build(asdict(spec)),
            specs,
        )
        deployed = self.deployer.deploy(artifacts)
        return {
            "built": [str(path) for path in artifacts],
            "deployed": deployed,
            "count": len(specs),
        }


def main() -> None:
    orchestrator = Orchestrator()
    orchestrator.run()


if __name__ == "__main__":
    main()
