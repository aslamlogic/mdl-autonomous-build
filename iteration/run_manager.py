import json
import os
from datetime import datetime
from typing import Dict, Any


class RunManager:
    """
    Manages per-run state snapshots.
    """

    def __init__(self, runs_dir: str = "runs"):
        self.runs_dir = runs_dir
        os.makedirs(self.runs_dir, exist_ok=True)

    def _ts(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def save_iteration_state(
        self,
        run_id: str,
        iteration_no: int,
        spec_text: str,
        validation_result: Dict[str, Any],
        constraints: list
    ) -> str:
        path = os.path.join(self.runs_dir, f"{run_id}_iteration_{iteration_no}.json")
        payload = {
            "run_id": run_id,
            "iteration_no": iteration_no,
            "timestamp": self._ts(),
            "spec_text": spec_text,
            "validation_result": validation_result,
            "constraints": constraints
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return path
