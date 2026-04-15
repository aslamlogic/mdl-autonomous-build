"""
iteration/queue_manager.py

Run queue and concurrency limiter for the Meta Software Production System.

Purpose
-------
1. Prevent uncontrolled thread explosion.
2. Enforce a maximum number of concurrent runs.
3. Queue excess runs deterministically.
4. Promote queued runs automatically when capacity becomes available.

Storage
-------
run_queue.json

Structure
---------
{
  "active_runs": [
    {
      "run_id": "...",
      "project_id": "...",
      "status": "running",
      "started_at": "..."
    }
  ],
  "queued_runs": [
    {
      "run_id": "...",
      "project_id": "...",
      "spec": {...},
      "enqueued_at": "..."
    }
  ],
  "max_concurrent_runs": 3
}

Notes
-----
- This is a file-backed queue suitable for the current system stage.
- It is deterministic and simple.
- It does not yet implement OS-level file locks.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


QUEUE_PATH = Path("run_queue.json")
DEFAULT_MAX_CONCURRENT_RUNS = 3

_queue_lock = Lock()


# ============================================================
# CORE LOAD / SAVE
# ============================================================

def load_queue() -> Dict[str, Any]:
    with _queue_lock:
        if not QUEUE_PATH.exists():
            data = {
                "active_runs": [],
                "queued_runs": [],
                "max_concurrent_runs": DEFAULT_MAX_CONCURRENT_RUNS,
            }
            save_queue(data)
            return data

        with QUEUE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Queue root must be a JSON object")

        data.setdefault("active_runs", [])
        data.setdefault("queued_runs", [])
        data.setdefault("max_concurrent_runs", DEFAULT_MAX_CONCURRENT_RUNS)

        return data


def save_queue(data: Dict[str, Any]) -> None:
    with _queue_lock:
        with QUEUE_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# ============================================================
# CONFIG
# ============================================================

def get_max_concurrent_runs() -> int:
    queue = load_queue()
    return int(queue.get("max_concurrent_runs", DEFAULT_MAX_CONCURRENT_RUNS))


def set_max_concurrent_runs(limit: int) -> Dict[str, Any]:
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("Concurrency limit must be a positive integer")

    queue = load_queue()
    queue["max_concurrent_runs"] = limit
    save_queue(queue)
    return queue


# ============================================================
# STATUS
# ============================================================

def list_active_runs() -> List[Dict[str, Any]]:
    return load_queue()["active_runs"]


def list_queued_runs() -> List[Dict[str, Any]]:
    return load_queue()["queued_runs"]


def has_capacity() -> bool:
    queue = load_queue()
    return len(queue["active_runs"]) < int(queue["max_concurrent_runs"])


def is_run_active(run_id: str) -> bool:
    return any(item.get("run_id") == run_id for item in list_active_runs())


def is_run_queued(run_id: str) -> bool:
    return any(item.get("run_id") == run_id for item in list_queued_runs())


# ============================================================
# ACTIVE RUN MANAGEMENT
# ============================================================

def register_active_run(run_id: str, project_id: str) -> Dict[str, Any]:
    queue = load_queue()

    if any(item.get("run_id") == run_id for item in queue["active_runs"]):
        return queue

    queue["active_runs"].append(
        {
            "run_id": run_id,
            "project_id": project_id,
            "status": "running",
            "started_at": now_iso(),
        }
    )
    save_queue(queue)
    return queue


def release_active_run(run_id: str) -> Dict[str, Any]:
    queue = load_queue()
    queue["active_runs"] = [
        item for item in queue["active_runs"]
        if item.get("run_id") != run_id
    ]
    save_queue(queue)
    return queue


# ============================================================
# QUEUE MANAGEMENT
# ============================================================

def enqueue_run(run_id: str, project_id: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    queue = load_queue()

    if any(item.get("run_id") == run_id for item in queue["queued_runs"]):
        return queue

    queue["queued_runs"].append(
        {
            "run_id": run_id,
            "project_id": project_id,
            "spec": spec if isinstance(spec, dict) else {},
            "enqueued_at": now_iso(),
        }
    )
    save_queue(queue)
    return queue


def dequeue_next_run() -> Optional[Dict[str, Any]]:
    queue = load_queue()

    if not queue["queued_runs"]:
        return None

    next_run = queue["queued_runs"].pop(0)
    save_queue(queue)
    return next_run


def maybe_promote_next_queued_run() -> Optional[Dict[str, Any]]:
    if not has_capacity():
        return None

    next_run = dequeue_next_run()
    if not next_run:
        return None

    register_active_run(
        run_id=next_run["run_id"],
        project_id=next_run["project_id"],
    )
    return next_run


# ============================================================
# UTIL
# ============================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
