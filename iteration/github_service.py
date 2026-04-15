"""
iteration/github_service.py

Dynamic GitHub repository provisioning and push support
for the Meta Software Production System.

Purpose
-------
1. Create a fresh GitHub repository per build/project.
2. Initialize a local workspace as a Git repository if needed.
3. Commit generated code.
4. Push to the newly created remote repository.
5. Return deterministic structured results.

Environment variables
---------------------
Required:
- GITHUB_TOKEN
- GITHUB_OWNER

Optional:
- GITHUB_API_BASE_URL             default: https://api.github.com
- GITHUB_DEFAULT_BRANCH           default: main
- GITHUB_REPO_VISIBILITY          values: private/public   default: private
- GITHUB_OWNER_TYPE               values: user/org         default: user

Notes
-----
- If GITHUB_OWNER_TYPE=org, the code uses the org repo creation endpoint.
- If GITHUB_OWNER_TYPE=user, the code uses the authenticated user repo creation endpoint.
- Push uses token-authenticated HTTPS remote URLs.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import requests


DEFAULT_GITHUB_API_BASE_URL = os.getenv("GITHUB_API_BASE_URL", "https://api.github.com")
DEFAULT_GITHUB_DEFAULT_BRANCH = os.getenv("GITHUB_DEFAULT_BRANCH", "main")
DEFAULT_GITHUB_REPO_VISIBILITY = os.getenv("GITHUB_REPO_VISIBILITY", "private").strip().lower()
DEFAULT_GITHUB_OWNER_TYPE = os.getenv("GITHUB_OWNER_TYPE", "user").strip().lower()


# ============================================================
# PUBLIC API
# ============================================================

def provision_repository(
    repo_name: str,
    local_repo_path: str,
    description: str = "",
    owner: Optional[str] = None,
    owner_type: Optional[str] = None,
    private: Optional[bool] = None,
    default_branch: Optional[str] = None,
    auto_init: bool = False,
) -> Dict[str, Any]:
    """
    Create a GitHub repository and push the local workspace.

    Returns
    -------
    Structured result including repo metadata and push outcome.
    """
    resolved_owner = (owner or os.getenv("GITHUB_OWNER", "")).strip()
    resolved_owner_type = (owner_type or DEFAULT_GITHUB_OWNER_TYPE).strip().lower()
    resolved_branch = (default_branch or DEFAULT_GITHUB_DEFAULT_BRANCH).strip()
    resolved_private = _resolve_private_flag(private)

    if not resolved_owner:
        return _failure(
            error_type="github_unconfigured",
            error_message="GITHUB_OWNER is not set",
            diagnostics={"stage": "preflight"},
        )

    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        return _failure(
            error_type="github_unconfigured",
            error_message="GITHUB_TOKEN is not set",
            diagnostics={"stage": "preflight"},
        )

    create_result = create_github_repo(
        repo_name=repo_name,
        description=description,
        owner=resolved_owner,
        owner_type=resolved_owner_type,
        private=resolved_private,
        auto_init=auto_init,
        default_branch=resolved_branch,
    )
    if not create_result["success"]:
        return create_result

    clone_url = create_result["repo"]["clone_url"]

    push_result = push_local_repo_to_remote(
        local_repo_path=local_repo_path,
        clone_url=clone_url,
        branch=resolved_branch,
    )
    if not push_result["success"]:
        return {
            "success": False,
            "error_type": push_result["error_type"],
            "error_message": push_result["error_message"],
            "repo": create_result["repo"],
            "diagnostics": {
                "stage": "push_local_repo_to_remote",
                "create_result": create_result,
                "push_result": push_result,
            },
        }

    return {
        "success": True,
        "error_type": None,
        "error_message": None,
        "repo": create_result["repo"],
        "push": push_result,
        "diagnostics": {
            "stage": "complete",
            "owner": resolved_owner,
            "owner_type": resolved_owner_type,
            "branch": resolved_branch,
        },
    }


def create_github_repo(
    repo_name: str,
    description: str = "",
    owner: Optional[str] = None,
    owner_type: Optional[str] = None,
    private: Optional[bool] = None,
    auto_init: bool = False,
    default_branch: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a GitHub repository for the authenticated user or an organization.
    """
    token = os.getenv("GITHUB_TOKEN", "").strip()
    resolved_owner = (owner or os.getenv("GITHUB_OWNER", "")).strip()
    resolved_owner_type = (owner_type or DEFAULT_GITHUB_OWNER_TYPE).strip().lower()
    resolved_private = _resolve_private_flag(private)
    resolved_branch = (default_branch or DEFAULT_GITHUB_DEFAULT_BRANCH).strip()

    if not token:
        return _failure(
            error_type="github_unconfigured",
            error_message="GITHUB_TOKEN is not set",
            diagnostics={"stage": "create_repo"},
        )

    if not repo_name or not isinstance(repo_name, str):
        return _failure(
            error_type="github_invalid_repo_name",
            error_message="Repository name is required",
            diagnostics={"stage": "create_repo"},
        )

    if resolved_owner_type not in {"user", "org"}:
        return _failure(
            error_type="github_invalid_owner_type",
            error_message=f"Unsupported owner type: {resolved_owner_type}",
            diagnostics={"stage": "create_repo"},
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    payload = {
        "name": repo_name,
        "description": description,
        "homepage": "",
        "private": resolved_private,
        "has_issues": True,
        "has_projects": False,
        "has_wiki": False,
        "auto_init": auto_init,
    }

    if resolved_owner_type == "org":
        if not resolved_owner:
            return _failure(
                error_type="github_unconfigured",
                error_message="GITHUB_OWNER must be set for organization repository creation",
                diagnostics={"stage": "create_repo"},
            )
        url = f"{DEFAULT_GITHUB_API_BASE_URL}/orgs/{resolved_owner}/repos"
    else:
        url = f"{DEFAULT_GITHUB_API_BASE_URL}/user/repos"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
    except Exception as exc:
        return _failure(
            error_type="github_request_error",
            error_message=str(exc),
            diagnostics={
                "stage": "create_repo",
                "url": url,
                "exception_class": exc.__class__.__name__,
            },
        )

    if response.status_code >= 400:
        return _failure(
            error_type="github_create_repo_failed",
            error_message=f"GitHub repository creation failed with HTTP {response.status_code}",
            diagnostics={
                "stage": "create_repo",
                "url": url,
                "status_code": response.status_code,
                "response_text": response.text[:2000],
            },
        )

    data = _safe_json(response)
    repo = {
        "name": data.get("name"),
        "full_name": data.get("full_name"),
        "html_url": data.get("html_url"),
        "clone_url": data.get("clone_url"),
        "default_branch": data.get("default_branch") or resolved_branch,
        "private": data.get("private"),
    }

    return {
        "success": True,
        "error_type": None,
        "error_message": None,
        "repo": repo,
        "diagnostics": {
            "stage": "create_repo",
            "owner": resolved_owner,
            "owner_type": resolved_owner_type,
        },
    }


def push_local_repo_to_remote(local_repo_path: str, clone_url: str, branch: Optional[str] = None) -> Dict[str, Any]:
    """
    Initialize/push local repo to GitHub remote.
    """
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        return _failure(
            error_type="github_unconfigured",
            error_message="GITHUB_TOKEN is not set",
            diagnostics={"stage": "push_repo"},
        )

    repo_path = Path(local_repo_path).resolve()
    if not repo_path.exists():
        return _failure(
            error_type="github_local_repo_missing",
            error_message=f"Local repository path does not exist: {repo_path}",
            diagnostics={"stage": "push_repo"},
        )

    target_branch = (branch or DEFAULT_GITHUB_DEFAULT_BRANCH).strip()
    auth_clone_url = _build_authenticated_clone_url(clone_url, token)

    try:
        _run_git(["git", "init"], cwd=repo_path)
        _run_git(["git", "checkout", "-B", target_branch], cwd=repo_path)

        if not (repo_path / ".gitignore").exists():
            (repo_path / ".gitignore").write_text(".DS_Store\n__pycache__/\n*.pyc\n.env\n", encoding="utf-8")

        _run_git(["git", "add", "."], cwd=repo_path)

        commit_needed = True
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if not status_result.stdout.strip():
            commit_needed = False

        if commit_needed:
            _run_git(["git", "config", "user.name", "sps-bot"], cwd=repo_path)
            _run_git(["git", "config", "user.email", "sps-bot@local.invalid"], cwd=repo_path)
            _run_git(["git", "commit", "-m", f"sps: initial provision on branch {target_branch}"], cwd=repo_path)

        remote_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if remote_result.returncode == 0:
            _run_git(["git", "remote", "remove", "origin"], cwd=repo_path)

        _run_git(["git", "remote", "add", "origin", auth_clone_url], cwd=repo_path)
        _run_git(["git", "push", "-u", "origin", target_branch], cwd=repo_path)

        return {
            "success": True,
            "error_type": None,
            "error_message": None,
            "diagnostics": {
                "stage": "push_repo",
                "local_repo_path": str(repo_path),
                "branch": target_branch,
            },
        }

    except Exception as exc:
        return _failure(
            error_type="github_push_failed",
            error_message=str(exc),
            diagnostics={
                "stage": "push_repo",
                "local_repo_path": str(repo_path),
                "branch": target_branch,
                "exception_class": exc.__class__.__name__,
            },
        )


# ============================================================
# INTERNALS
# ============================================================

def _resolve_private_flag(private: Optional[bool]) -> bool:
    if isinstance(private, bool):
        return private
    visibility = DEFAULT_GITHUB_REPO_VISIBILITY
    return visibility != "public"


def _build_authenticated_clone_url(clone_url: str, token: str) -> str:
    if clone_url.startswith("https://"):
        return clone_url.replace("https://", f"https://x-access-token:{token}@")
    raise ValueError(f"Unsupported clone URL: {clone_url}")


def _run_git(cmd: list[str], cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def _safe_json(response: requests.Response) -> Dict[str, Any]:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"raw": data}
    except Exception:
        return {"raw_text": response.text}


def _failure(error_type: str, error_message: str, diagnostics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "success": False,
        "error_type": error_type,
        "error_message": error_message,
        "diagnostics": diagnostics or {},
    }
