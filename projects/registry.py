"""
projects/registry.py

Multi-project registry for the Meta Software Production System.

Purpose
-------
1. Persist definitions for multiple software products.
2. Provide deterministic CRUD operations over project metadata.
3. Serve as the control-plane foundation for concurrent software production.
4. Keep project routing separate from run execution logic.

Storage
-------
Default registry file:
    projects/projects.json

Registry shape
--------------
{
  "projects": [
    {
      "project_id": "evidentia",
      "project_name": "Evidentia Legal Intelligence",
      "spec_path": "projects/evidentia/spec.json",
      "workspace_path": "projects/evidentia/workspace",
      "runs_path": "projects/evidentia/runs",
      "repo_url": "https://github.com/example/repo",
      "default_branch": "main",
      "deploy_provider": "render",
      "deploy_config": {
        "service_id": "srv-123",
        "health_path": "/health"
      },
      "validation_profile": {
        "require_health": True
      },
      "is_active": True,
      "created_at": "2026-04-15T12:00:00+00:00",
      "updated_at": "2026-04-15T12:00:00+00:00"
    }
  ]
}

Notes
-----
- This module is intentionally JSON-backed first.
- It is deterministic and file-based, suitable for the current system stage.
- It can later be swapped for SQLite/PostgreSQL without changing callers much.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_REGISTRY_PATH = Path("projects/projects.json")


# ============================================================
# PUBLIC API
# ============================================================

def load_registry(registry_path: str = str(DEFAULT_REGISTRY_PATH)) -> Dict[str, Any]:
    """
    Load the full project registry from disk.
    Creates an empty registry if none exists.
    """
    path = Path(registry_path)

    if not path.exists():
        empty = {"projects": []}
        _write_json(path, empty)
        return empty

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Project registry root must be a JSON object")

    projects = data.get("projects")
    if not isinstance(projects, list):
        raise ValueError("Project registry must contain a 'projects' list")

    return data


def save_registry(registry: Dict[str, Any], registry_path: str = str(DEFAULT_REGISTRY_PATH)) -> Dict[str, Any]:
    """
    Persist the full project registry to disk.
    """
    if not isinstance(registry, dict):
        raise ValueError("Registry must be a dictionary")

    projects = registry.get("projects")
    if not isinstance(projects, list):
        raise ValueError("Registry must contain a 'projects' list")

    path = Path(registry_path)
    _write_json(path, registry)
    return registry


def list_projects(registry_path: str = str(DEFAULT_REGISTRY_PATH), active_only: bool = False) -> List[Dict[str, Any]]:
    """
    Return all projects, optionally filtered to active only.
    """
    registry = load_registry(registry_path)
    projects = registry["projects"]

    if not active_only:
        return projects

    return [project for project in projects if bool(project.get("is_active", False))]


def get_project(project_id: str, registry_path: str = str(DEFAULT_REGISTRY_PATH)) -> Optional[Dict[str, Any]]:
    """
    Fetch a single project by project_id.
    Returns None if not found.
    """
    registry = load_registry(registry_path)

    for project in registry["projects"]:
        if project.get("project_id") == project_id:
            return project

    return None


def create_project(
    project_id: str,
    project_name: str,
    spec_path: str,
    workspace_path: str,
    runs_path: str,
    repo_url: str,
    default_branch: str = "main",
    deploy_provider: str = "render",
    deploy_config: Optional[Dict[str, Any]] = None,
    validation_profile: Optional[Dict[str, Any]] = None,
    is_active: bool = True,
    registry_path: str = str(DEFAULT_REGISTRY_PATH),
) -> Dict[str, Any]:
    """
    Create a new project record in the registry.

    Raises
    ------
    ValueError if project_id already exists or fields are invalid.
    """
    registry = load_registry(registry_path)

    if get_project(project_id, registry_path=registry_path) is not None:
        raise ValueError(f"Project already exists: {project_id}")

    project = _build_project_record(
        project_id=project_id,
        project_name=project_name,
        spec_path=spec_path,
        workspace_path=workspace_path,
        runs_path=runs_path,
        repo_url=repo_url,
        default_branch=default_branch,
        deploy_provider=deploy_provider,
        deploy_config=deploy_config or {},
        validation_profile=validation_profile or {},
        is_active=is_active,
        created_at=_now_iso(),
        updated_at=_now_iso(),
    )

    registry["projects"].append(project)
    save_registry(registry, registry_path=registry_path)
    return project


def update_project(
    project_id: str,
    updates: Dict[str, Any],
    registry_path: str = str(DEFAULT_REGISTRY_PATH),
) -> Dict[str, Any]:
    """
    Update an existing project with partial fields.

    Protected fields:
    - project_id
    - created_at
    """
    if not isinstance(updates, dict):
        raise ValueError("Updates must be a dictionary")

    registry = load_registry(registry_path)
    projects = registry["projects"]

    for index, project in enumerate(projects):
        if project.get("project_id") != project_id:
            continue

        updated = dict(project)

        for key, value in updates.items():
            if key in {"project_id", "created_at"}:
                continue
            updated[key] = value

        updated["updated_at"] = _now_iso()
        _validate_project_record(updated)

        projects[index] = updated
        save_registry(registry, registry_path=registry_path)
        return updated

    raise ValueError(f"Project not found: {project_id}")


def set_project_active_state(
    project_id: str,
    is_active: bool,
    registry_path: str = str(DEFAULT_REGISTRY_PATH),
) -> Dict[str, Any]:
    """
    Enable or disable a project.
    """
    return update_project(
        project_id=project_id,
        updates={"is_active": bool(is_active)},
        registry_path=registry_path,
    )


def delete_project(project_id: str, registry_path: str = str(DEFAULT_REGISTRY_PATH)) -> Dict[str, Any]:
    """
    Delete a project from the registry.

    Returns
    -------
    Dict with deletion outcome and deleted project_id.
    """
    registry = load_registry(registry_path)
    original_len = len(registry["projects"])

    registry["projects"] = [
        project for project in registry["projects"]
        if project.get("project_id") != project_id
    ]

    if len(registry["projects"]) == original_len:
        raise ValueError(f"Project not found: {project_id}")

    save_registry(registry, registry_path=registry_path)

    return {
        "success": True,
        "deleted_project_id": project_id,
        "remaining_projects": len(registry["projects"]),
    }


def ensure_project_directories(project: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure on-disk directories exist for a project.
    """
    if not isinstance(project, dict):
        raise ValueError("Project must be a dictionary")

    workspace_path = Path(project["workspace_path"])
    runs_path = Path(project["runs_path"])
    spec_parent = Path(project["spec_path"]).parent

    created = []

    for target in (workspace_path, runs_path, spec_parent):
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))

    return {
        "success": True,
        "created_paths": created,
        "workspace_path": str(workspace_path),
        "runs_path": str(runs_path),
    }


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _build_project_record(
    project_id: str,
    project_name: str,
    spec_path: str,
    workspace_path: str,
    runs_path: str,
    repo_url: str,
    default_branch: str,
    deploy_provider: str,
    deploy_config: Dict[str, Any],
    validation_profile: Dict[str, Any],
    is_active: bool,
    created_at: str,
    updated_at: str,
) -> Dict[str, Any]:
    project = {
        "project_id": project_id,
        "project_name": project_name,
        "spec_path": spec_path,
        "workspace_path": workspace_path,
        "runs_path": runs_path,
        "repo_url": repo_url,
        "default_branch": default_branch,
        "deploy_provider": deploy_provider,
        "deploy_config": deploy_config,
        "validation_profile": validation_profile,
        "is_active": bool(is_active),
        "created_at": created_at,
        "updated_at": updated_at,
    }

    _validate_project_record(project)
    return project


def _validate_project_record(project: Dict[str, Any]) -> None:
    required_string_fields = [
        "project_id",
        "project_name",
        "spec_path",
        "workspace_path",
        "runs_path",
        "repo_url",
        "default_branch",
        "deploy_provider",
        "created_at",
        "updated_at",
    ]

    for field in required_string_fields:
        value = project.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Project field '{field}' must be a non-empty string")

    if not isinstance(project.get("deploy_config"), dict):
        raise ValueError("Project field 'deploy_config' must be a dictionary")

    if not isinstance(project.get("validation_profile"), dict):
        raise ValueError("Project field 'validation_profile' must be a dictionary")

    if not isinstance(project.get("is_active"), bool):
        raise ValueError("Project field 'is_active' must be a boolean")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# OPTIONAL DEBUG ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    sample_project_id = "sample_project"

    if get_project(sample_project_id) is None:
        created = create_project(
            project_id=sample_project_id,
            project_name="Sample Project",
            spec_path="projects/sample_project/spec.json",
            workspace_path="projects/sample_project/workspace",
            runs_path="projects/sample_project/runs",
            repo_url="https://github.com/example/sample-project",
            default_branch="main",
            deploy_provider="render",
            deploy_config={"service_id": "srv-sample", "health_path": "/health"},
            validation_profile={"require_health": True},
            is_active=True,
        )
        ensure_project_directories(created)
        print(json.dumps(created, indent=2))
    else:
        print(json.dumps(get_project(sample_project_id), indent=2))
