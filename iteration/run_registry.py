"""
iteration/run_registry.py

Run registry for tracking all executions across projects.

Purpose
-------
1. Track all runs (active, completed, failed)
2. Enable multi-run orchestration
3. Provide status lookup for API layer
4. Support concurrent execution safely (basic level)

Storage
-------
runs_registry.json

Structure
---------
{
  "runs": [
    {
      "run_id": "...",
      "project_id": "...",
      "status": "running | completed | failed",
      "current_iteration": 1,
      "max_iterations": 3,
      "created_at": "...",
      "updated_at": "...",
      "live_url": null,
      "error": null
    }
  ]
}
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


REGISTRY_PATH = Path("runs_registry.json")


# ============================================================
# CORE LOAD / SAVE
# ============================================================

def load_registry() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        data = {"runs": []}
        save_registry(data)
        return data

    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_registry(data: Dict[str, Any]) -> None:
    with REGISTRY_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ============================================================
# CREATE RUN
# ============================================================

def create_run(run_id: str, project_id: str, max_iterations: int) -> Dict[str, Any]:

    registry = load_registry()

    run = {
        "run_id": run_id,
        "project_id": project_id,
        "status": "running",
        "current_iteration": 0,
        "max_iterations": max_iterations,
        "created_at": now(),
        "updated_at": now(),
        "live_url": None,
        "error": None
    }

    registry["runs"].append(run)
    save_registry(registry)

    return run


# ============================================================
# UPDATE RUN
# ============================================================

def update_run(run_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:

    registry = load_registry()

    for i, run in enumerate(registry["runs"]):
        if run["run_id"] != run_id:
            continue

        updated = dict(run)

        for k, v in updates.items():
            updated[k] = v

        updated["updated_at"] = now()

        registry["runs"][i] = updated
        save_registry(registry)

        return updated

    return None


# ============================================================
# GET RUN
# ============================================================

def get_run(run_id: str) -> Optional[Dict[str, Any]]:

    registry = load_registry()

    for run in registry["runs"]:
        if run["run_id"] == run_id:
            return run

    return None


# ============================================================
# LIST RUNS
# ============================================================

def list_runs(project_id: Optional[str] = None) -> List[Dict[str, Any]]:

    registry = load_registry()

    if not project_id:
        return registry["runs"]

    return [r for r in registry["runs"] if r["project_id"] == project_id]


# ============================================================
# STATUS HELPERS
# ============================================================

def mark_completed(run_id: str, live_url: Optional[str] = None):

    return update_run(run_id, {
        "status": "completed",
        "live_url": live_url
    })


def mark_failed(run_id: str, error: str):

    return update_run(run_id, {
        "status": "failed",
        "error": error
    })


def update_iteration(run_id: str, iteration_no: int):

    return update_run(run_id, {
        "current_iteration": iteration_no
    })


# ============================================================
# UTIL
# ============================================================

def now():
    return datetime.now(timezone.utc).isoformat()
