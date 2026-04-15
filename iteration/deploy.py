"""
iteration/deploy.py

Project-aware Render deployment loop for the Meta Software Production System.

Purpose
-------
1. Route deployment per project rather than through a shared global config.
2. Read deployment configuration from the project registry.
3. Support:
   - project-specific deploy hook
   - project-specific Render service ID
   - project-specific health path
   - project-specific API key override
4. Return deterministic structured deployment results.

Project deploy_config shape
---------------------------
{
  "service_id": "srv-xxxx",
  "health_path": "/health",
  "deploy_hook_url": "https://api.render.com/deploy/....",
  "api_key_env": "RENDER_API_KEY_EVIDENTIA",
  "base_url": "https://api.render.com/v1"
}

Fallback behaviour
------------------
If a value is not present in deploy_config, the module falls back to:
- env vars:
    RENDER_API_KEY
    RENDER_SERVICE_ID
    RENDER_DEPLOY_HOOK_URL
    RENDER_BASE_URL
    RENDER_HEALTH_PATH
- then deterministic failure if still missing.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

import requests

from projects.registry import get_project


DEFAULT_RENDER_BASE_URL = "https://api.render.com/v1"
DEFAULT_HEALTH_PATH = "/health"
DEFAULT_POLL_INTERVAL_SECONDS = 5
DEFAULT_POLL_TIMEOUT_SECONDS = 300


# ============================================================
# PUBLIC API
# ============================================================

def deploy_system(
    project_id: Optional[str] = None,
    base_dir: str = ".",
    validation_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Project-aware deployment entrypoint.

    Parameters
    ----------
    project_id:
        Registry project identifier. Required for per-project deployment hardening.
    base_dir:
        Kept for compatibility. Not used directly here.
    validation_report:
        If provided and failed, deployment is blocked.

    Returns
    -------
    Structured deployment result.
    """
    if isinstance(validation_report, dict):
        if not validation_report.get("overall_pass", False):
            return _failure(
                error_type="deployment_blocked",
                error_message="Deployment blocked because validation did not pass",
                diagnostics={"stage": "preflight_validation_gate", "project_id": project_id},
            )

    config_result = _resolve_project_deploy_config(project_id)
    if not config_result["success"]:
        return config_result

    deploy_config = config_result["deploy_config"]

    trigger_result = _trigger_deployment(deploy_config)
    if not trigger_result["success"]:
        return trigger_result

    service_result = _poll_for_live_service(deploy_config)
    if not service_result["success"]:
        return service_result

    live_url = service_result["live_url"]

    probe_result = probe_live_url(live_url=live_url, health_path=deploy_config["health_path"])
    if not probe_result["success"]:
        return {
            "success": False,
            "deployment_status": "deployed_but_probe_failed",
            "live_url": live_url,
            "error_type": probe_result["error_type"],
            "error_message": probe_result["error_message"],
            "diagnostics": {
                "stage": "live_probe",
                "project_id": project_id,
                "deploy_config": _safe_deploy_config_for_log(deploy_config),
                "service_result": service_result,
                "probe_result": probe_result,
            },
        }

    return {
        "success": True,
        "deployment_status": "succeeded",
        "live_url": live_url,
        "error_type": None,
        "error_message": None,
        "diagnostics": {
            "stage": "complete",
            "project_id": project_id,
            "deploy_config": _safe_deploy_config_for_log(deploy_config),
            "trigger_result": trigger_result,
            "service_result": service_result,
            "probe_result": probe_result,
        },
    }


def probe_live_url(live_url: str, health_path: str = DEFAULT_HEALTH_PATH) -> Dict[str, Any]:
    """
    Probe the live service health endpoint deterministically.
    """
    if not isinstance(live_url, str) or not live_url.strip():
        return _failure(
            error_type="live_probe_invalid_url",
            error_message="Live URL is missing or invalid",
            diagnostics={"stage": "probe_live_url"},
        )

    path = health_path if isinstance(health_path, str) and health_path.strip() else DEFAULT_HEALTH_PATH
    if not path.startswith("/"):
        path = "/" + path

    target = live_url.rstrip("/") + path

    try:
        response = requests.get(target, timeout=20)
    except Exception as exc:
        return _failure(
            error_type="live_probe_request_error",
            error_message=str(exc),
            diagnostics={
                "stage": "probe_live_url",
                "target": target,
                "exception_class": exc.__class__.__name__,
            },
        )

    if response.status_code >= 400:
        return _failure(
            error_type="live_probe_http_error",
            error_message=f"Health endpoint returned HTTP {response.status_code}",
            diagnostics={
                "stage": "probe_live_url",
                "target": target,
                "status_code": response.status_code,
                "response_text": response.text[:1000],
            },
        )

    try:
        payload = response.json()
    except Exception as exc:
        return _failure(
            error_type="live_probe_non_json",
            error_message=f"Health endpoint did not return JSON: {exc}",
            diagnostics={
                "stage": "probe_live_url",
                "target": target,
                "response_text": response.text[:1000],
                "exception_class": exc.__class__.__name__,
            },
        )

    if not isinstance(payload, dict):
        return _failure(
            error_type="live_probe_schema_error",
            error_message="Health endpoint JSON payload is not an object",
            diagnostics={
                "stage": "probe_live_url",
                "target": target,
                "payload": payload,
            },
        )

    return {
        "success": True,
        "status_code": response.status_code,
        "target": target,
        "payload": payload,
        "error_type": None,
        "error_message": None,
        "diagnostics": {"stage": "probe_live_url"},
    }


# ============================================================
# PROJECT CONFIG RESOLUTION
# ============================================================

def _resolve_project_deploy_config(project_id: Optional[str]) -> Dict[str, Any]:
    if not project_id:
        return _failure(
            error_type="project_deploy_unconfigured",
            error_message="project_id is required for project-aware deployment",
            diagnostics={"stage": "resolve_project_deploy_config"},
        )

    project = get_project(project_id)
    if not project:
        return _failure(
            error_type="project_not_found",
            error_message=f"Project not found: {project_id}",
            diagnostics={"stage": "resolve_project_deploy_config", "project_id": project_id},
        )

    deploy_config = project.get("deploy_config", {})
    if not isinstance(deploy_config, dict):
        return _failure(
            error_type="project_deploy_unconfigured",
            error_message=f"Project deploy_config is invalid for project: {project_id}",
            diagnostics={"stage": "resolve_project_deploy_config", "project_id": project_id},
        )

    api_key_env = deploy_config.get("api_key_env", "RENDER_API_KEY")
    if not isinstance(api_key_env, str) or not api_key_env.strip():
        api_key_env = "RENDER_API_KEY"

    resolved = {
        "project_id": project_id,
        "project_name": project.get("project_name", project_id),
        "deploy_provider": project.get("deploy_provider", "render"),
        "api_key": os.getenv(api_key_env, "").strip(),
        "api_key_env": api_key_env,
        "service_id": _first_non_empty_string(
            deploy_config.get("service_id"),
            os.getenv("RENDER_SERVICE_ID", "").strip(),
        ),
        "deploy_hook_url": _first_non_empty_string(
            deploy_config.get("deploy_hook_url"),
            os.getenv("RENDER_DEPLOY_HOOK_URL", "").strip(),
        ),
        "base_url": _first_non_empty_string(
            deploy_config.get("base_url"),
            os.getenv("RENDER_BASE_URL", "").strip(),
            DEFAULT_RENDER_BASE_URL,
        ),
        "health_path": _first_non_empty_string(
            deploy_config.get("health_path"),
            os.getenv("RENDER_HEALTH_PATH", "").strip(),
            DEFAULT_HEALTH_PATH,
        ),
        "poll_interval_seconds": _coerce_int(
            deploy_config.get("poll_interval_seconds"),
            _coerce_int(os.getenv("RENDER_POLL_INTERVAL_SECONDS"), DEFAULT_POLL_INTERVAL_SECONDS),
        ),
        "poll_timeout_seconds": _coerce_int(
            deploy_config.get("poll_timeout_seconds"),
            _coerce_int(os.getenv("RENDER_POLL_TIMEOUT_SECONDS"), DEFAULT_POLL_TIMEOUT_SECONDS),
        ),
    }

    provider = str(resolved["deploy_provider"]).lower().strip()
    if provider != "render":
        return _failure(
            error_type="unsupported_deploy_provider",
            error_message=f"Unsupported deploy provider for project {project_id}: {provider}",
            diagnostics={"stage": "resolve_project_deploy_config", "project_id": project_id},
        )

    if resolved["deploy_hook_url"]:
        return {
            "success": True,
            "deploy_config": resolved,
            "error_type": None,
            "error_message": None,
            "diagnostics": {
                "stage": "resolve_project_deploy_config",
                "project_id": project_id,
                "mode": "deploy_hook",
                "deploy_config": _safe_deploy_config_for_log(resolved),
            },
        }

    if not resolved["api_key"]:
        return _failure(
            error_type="render_unconfigured",
            error_message=f"Render API key is not configured for project {project_id} via env var {api_key_env}",
            diagnostics={
                "stage": "resolve_project_deploy_config",
                "project_id": project_id,
                "api_key_env": api_key_env,
            },
        )

    if not resolved["service_id"]:
        return _failure(
            error_type="render_unconfigured",
            error_message=f"Render service_id is not configured for project {project_id}",
            diagnostics={
                "stage": "resolve_project_deploy_config",
                "project_id": project_id,
            },
        )

    return {
        "success": True,
        "deploy_config": resolved,
        "error_type": None,
        "error_message": None,
        "diagnostics": {
            "stage": "resolve_project_deploy_config",
            "project_id": project_id,
            "mode": "render_api",
            "deploy_config": _safe_deploy_config_for_log(resolved),
        },
    }


# ============================================================
# TRIGGER
# ============================================================

def _trigger_deployment(deploy_config: Dict[str, Any]) -> Dict[str, Any]:
    deploy_hook_url = deploy_config.get("deploy_hook_url", "")
    if isinstance(deploy_hook_url, str) and deploy_hook_url.strip():
        return _trigger_via_deploy_hook(deploy_config)

    return _trigger_via_render_api(deploy_config)


def _trigger_via_deploy_hook(deploy_config: Dict[str, Any]) -> Dict[str, Any]:
    deploy_hook_url = deploy_config["deploy_hook_url"]

    try:
        response = requests.post(deploy_hook_url, timeout=30)
    except Exception as exc:
        return _failure(
            error_type="render_trigger_error",
            error_message=str(exc),
            diagnostics={
                "stage": "trigger_deploy_hook",
                "project_id": deploy_config.get("project_id"),
                "exception_class": exc.__class__.__name__,
            },
        )

    if response.status_code >= 400:
        return _failure(
            error_type="render_trigger_http_error",
            error_message=f"Deploy hook returned HTTP {response.status_code}",
            diagnostics={
                "stage": "trigger_deploy_hook",
                "project_id": deploy_config.get("project_id"),
                "status_code": response.status_code,
                "response_text": response.text[:1000],
            },
        )

    return {
        "success": True,
        "trigger_mode": "deploy_hook",
        "error_type": None,
        "error_message": None,
        "diagnostics": {
            "stage": "trigger_deploy_hook",
            "project_id": deploy_config.get("project_id"),
            "status_code": response.status_code,
            "response_text": response.text[:1000],
        },
    }


def _trigger_via_render_api(deploy_config: Dict[str, Any]) -> Dict[str, Any]:
    api_key = deploy_config["api_key"]
    service_id = deploy_config["service_id"]
    base_url = deploy_config["base_url"]

    url = f"{base_url}/services/{service_id}/deploys"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json={}, timeout=30)
    except Exception as exc:
        return _failure(
            error_type="render_trigger_error",
            error_message=str(exc),
            diagnostics={
                "stage": "trigger_render_api",
                "project_id": deploy_config.get("project_id"),
                "url": url,
                "exception_class": exc.__class__.__name__,
            },
        )

    if response.status_code >= 400:
        return _failure(
            error_type="render_trigger_http_error",
            error_message=f"Render deploy API returned HTTP {response.status_code}",
            diagnostics={
                "stage": "trigger_render_api",
                "project_id": deploy_config.get("project_id"),
                "url": url,
                "status_code": response.status_code,
                "response_text": response.text[:1000],
            },
        )

    payload = _safe_json_response(response)

    return {
        "success": True,
        "trigger_mode": "render_api",
        "error_type": None,
        "error_message": None,
        "diagnostics": {
            "stage": "trigger_render_api",
            "project_id": deploy_config.get("project_id"),
            "status_code": response.status_code,
            "payload": payload,
        },
    }


# ============================================================
# POLLING
# ============================================================

def _poll_for_live_service(deploy_config: Dict[str, Any]) -> Dict[str, Any]:
    api_key = deploy_config.get("api_key", "")
    service_id = deploy_config.get("service_id", "")
    base_url = deploy_config.get("base_url", DEFAULT_RENDER_BASE_URL)
    deploy_hook_url = deploy_config.get("deploy_hook_url", "")
    poll_interval_seconds = deploy_config.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)
    poll_timeout_seconds = deploy_config.get("poll_timeout_seconds", DEFAULT_POLL_TIMEOUT_SECONDS)

    if deploy_hook_url and (not api_key or not service_id):
        return _failure(
            error_type="render_poll_unconfigured",
            error_message=(
                f"Polling requires api key and service_id for project {deploy_config.get('project_id')}, "
                "even when using a deploy hook"
            ),
            diagnostics={
                "stage": "poll_preflight",
                "project_id": deploy_config.get("project_id"),
            },
        )

    url = f"{base_url}/services/{service_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    deadline = time.time() + poll_timeout_seconds
    last_payload: Optional[Dict[str, Any]] = None

    while time.time() < deadline:
        try:
            response = requests.get(url, headers=headers, timeout=30)
        except Exception as exc:
            return _failure(
                error_type="render_poll_error",
                error_message=str(exc),
                diagnostics={
                    "stage": "poll_service",
                    "project_id": deploy_config.get("project_id"),
                    "url": url,
                    "exception_class": exc.__class__.__name__,
                },
            )

        if response.status_code >= 400:
            return _failure(
                error_type="render_poll_http_error",
                error_message=f"Render service status API returned HTTP {response.status_code}",
                diagnostics={
                    "stage": "poll_service",
                    "project_id": deploy_config.get("project_id"),
                    "url": url,
                    "status_code": response.status_code,
                    "response_text": response.text[:1000],
                },
            )

        payload = _safe_json_response(response)
        last_payload = payload if isinstance(payload, dict) else None

        live_url = _extract_live_url(payload)
        service_state = _extract_service_state(payload)

        if live_url and service_state in {"live", "deploying", "available", "running"}:
            return {
                "success": True,
                "live_url": live_url,
                "service_state": service_state,
                "error_type": None,
                "error_message": None,
                "diagnostics": {
                    "stage": "poll_service",
                    "project_id": deploy_config.get("project_id"),
                    "payload": payload,
                },
            }

        time.sleep(poll_interval_seconds)

    return _failure(
        error_type="render_poll_timeout",
        error_message="Timed out waiting for live Render service URL",
        diagnostics={
            "stage": "poll_service",
            "project_id": deploy_config.get("project_id"),
            "last_payload": last_payload,
            "timeout_seconds": poll_timeout_seconds,
        },
    )


def _extract_live_url(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None

    candidates = [
        payload.get("service", {}).get("serviceDetails", {}).get("url") if isinstance(payload.get("service"), dict) else None,
        payload.get("serviceDetails", {}).get("url") if isinstance(payload.get("serviceDetails"), dict) else None,
        payload.get("url"),
        payload.get("service", {}).get("url") if isinstance(payload.get("service"), dict) else None,
    ]

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            if candidate.startswith("http://") or candidate.startswith("https://"):
                return candidate.strip()

    return None


def _extract_service_state(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "unknown"

    candidates = [
        payload.get("service", {}).get("suspended") if isinstance(payload.get("service"), dict) else None,
        payload.get("suspended"),
        payload.get("status"),
        payload.get("service", {}).get("status") if isinstance(payload.get("service"), dict) else None,
    ]

    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
        if isinstance(value, bool):
            return "suspended" if value else "live"

    return "unknown"


# ============================================================
# UTILITIES
# ============================================================

def _safe_json_response(response: requests.Response) -> Any:
    try:
        return response.json()
    except Exception:
        try:
            return {"raw_text": response.text}
        except Exception:
            return {"raw_text": "<unreadable response>"}


def _safe_deploy_config_for_log(deploy_config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "project_id": deploy_config.get("project_id"),
        "project_name": deploy_config.get("project_name"),
        "deploy_provider": deploy_config.get("deploy_provider"),
        "api_key_env": deploy_config.get("api_key_env"),
        "service_id": deploy_config.get("service_id"),
        "deploy_hook_url_present": bool(deploy_config.get("deploy_hook_url")),
        "base_url": deploy_config.get("base_url"),
        "health_path": deploy_config.get("health_path"),
        "poll_interval_seconds": deploy_config.get("poll_interval_seconds"),
        "poll_timeout_seconds": deploy_config.get("poll_timeout_seconds"),
    }


def _first_non_empty_string(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _failure(error_type: str, error_message: str, diagnostics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "success": False,
        "deployment_status": "failed",
        "live_url": None,
        "error_type": error_type,
        "error_message": error_message,
        "diagnostics": diagnostics or {},
    }


# ============================================================
# OPTIONAL DEBUG ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    result = deploy_system(project_id="default", validation_report={"overall_pass": True})
    print(json.dumps(result, indent=2))
