from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from .app_builder import AppBuilder
from .deployer import Deployer
from .engine_builder import EngineBuilder


class Executor:
    def __init__(self, max_workers: int = 4, apps_dir: str = "apps/", meta_dir: str = "meta_system/"):
        self.max_workers = max_workers
        self.app_builder = AppBuilder(apps_dir=apps_dir)
        self.engine_builder = EngineBuilder(meta_dir=meta_dir)
        self.deployer = Deployer()

    def run_one(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        engine_path = self.engine_builder.build(spec)
        app_path = self.app_builder.build(spec)
        deploy_path = self.deployer.deploy(app_path, spec)
        return {"name": spec.get("name"), "engine_path": engine_path, "app_path": app_path, "deploy_path": deploy_path}

    def run_many(self, specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if not specs:
            return results
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self.run_one, spec): spec for spec in specs}
            for future in as_completed(futures):
                results.append(future.result())
        return results
