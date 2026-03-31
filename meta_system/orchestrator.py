from __future__ import annotations

from typing import Any, Dict, List

from meta_system.app_builder import AppBuilder
from meta_system.deployer import Deployer
from meta_system.engine_builder import EngineBuilder
from meta_system.executor import Executor
from meta_system.spec_loader import SpecLoader


class Orchestrator:
    def __init__(self, app_specs_dir: str = "specs/apps/", apps_dir: str = "apps/", max_workers: int | None = None) -> None:
        self.spec_loader = SpecLoader(app_specs_dir)
        self.app_builder = AppBuilder(apps_dir)
        self.engine_builder = EngineBuilder(apps_dir)
        self.deployer = Deployer(apps_dir)
        self.executor = Executor(max_workers=max_workers)

    def _process_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        app_result = self.app_builder.build(spec)
        engine_result = self.engine_builder.build(spec)
        deploy_result = self.deployer.deploy({**app_result, **engine_result})
        return {"spec": spec.get("name") or spec.get("app_name") or "app", **app_result, **engine_result, **deploy_result}

    def run(self) -> List[Dict[str, Any]]:
        specs = self.spec_loader.load_specs()
        return self.executor.run_parallel(specs, self._process_spec)


if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run()
