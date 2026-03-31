from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

from .spec_loader import load_app_specs
from .app_builder import AppBuilder
from .engine_builder import EngineBuilder
from .deployer import Deployer
from .executor import TaskExecutor


class Orchestrator:
    def __init__(self, app_specs_dir: str = "specs/apps/", meta_system_dir: str = "meta_system/", apps_dir: str = "apps/") -> None:
        self.app_specs_dir = Path(app_specs_dir)
        self.meta_system_dir = Path(meta_system_dir)
        self.apps_dir = Path(apps_dir)
        self.executor = TaskExecutor()
        self.engine_builder = EngineBuilder(self.executor)
        self.app_builder = AppBuilder(self.executor, self.engine_builder, self.apps_dir)
        self.deployer = Deployer(self.executor, self.apps_dir)

    def run(self) -> Dict[str, Any]:
        specs = load_app_specs(self.app_specs_dir)
        results: List[Dict[str, Any]] = []

        def build_and_deploy(spec: Dict[str, Any]) -> Dict[str, Any]:
            app_result = self.app_builder.build(spec)
            deploy_result = self.deployer.deploy(spec, app_result)
            return {"app": spec.get("name", "unknown"), "build": app_result, "deploy": deploy_result}

        if not specs:
            return {"status": "no_specs_found", "results": []}

        if len(specs) == 1:
            results.append(build_and_deploy(specs[0]))
        else:
            with ThreadPoolExecutor(max_workers=min(8, len(specs))) as pool:
                futures = {pool.submit(build_and_deploy, spec): spec for spec in specs}
                for future in as_completed(futures):
                    results.append(future.result())

        return {"status": "success", "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Meta system orchestrator")
    parser.add_argument("--app-specs-dir", default="specs/apps/", help="Directory containing app specs")
    parser.add_argument("--meta-system-dir", default="meta_system/", help="Meta system output directory")
    parser.add_argument("--apps-dir", default="apps/", help="Apps output directory")
    args = parser.parse_args()

    orchestrator = Orchestrator(args.app_specs_dir, args.meta_system_dir, args.apps_dir)
    result = orchestrator.run()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
