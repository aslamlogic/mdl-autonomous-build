import json
import os
from datetime import datetime
from typing import Dict, Any


class LoggingService:
    """
    JSONL logging service for deterministic run traces.
    """

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    def _ts(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def log(self, run_id: str, action: str, status: str, meta: Dict[str, Any] | None = None) -> str:
        path = os.path.join(self.log_dir, f"run_{run_id}.jsonl")
        entry = {
            "ts": self._ts(),
            "run_id": run_id,
            "action": action,
            "status": status,
            "meta": meta or {}
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return path
