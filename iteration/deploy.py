"""
iteration/deploy.py

Render deployment loop for the Meta Dev Launcher.

Purpose
-------
1. Trigger or verify deployment against Render after a successful validation cycle.
2. Poll deployment/live status deterministically.
3. Probe the live /health endpoint.
4. Return structured machine-readable deployment results for controller integration.

Environment variables
---------------------
Required for full Render API control:
- RENDER_API_KEY
- RENDER_SERVICE_ID

Optional:
- RENDER_BASE_URL               default: https://api.render.com/v1
- RENDER_DEPLOY_HOOK_URL        if present, deploy hook trigger is preferred
- RENDER_HEALTH_PATH            default: /health
- RENDER_POLL_INTERVAL_SECONDS  default: 5
- RENDER_POLL_TIMEOUT_SECONDS   default: 300

Notes
-----
- This module is safe if Render credentials are missing: it returns a structured failure.
- It supports two deployment trigger modes:
  1. Deploy hook URL
  2. Render API service deploy endpoint
- It also supports a passive verification mode if the service is already live.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

import requests


DEFAULT_RENDER_BASE_URL = os.getenv("RENDER_BASE_URL", "https://api.render.com/v1")
DEFAULT_HEALTH_PATH = os.getenv("RENDER_HEALTH_PATH", "/health")
DEFAULT_POLL_INTERVAL_SECONDS = int(os.getenv("RENDER_POLL_INTERVAL_SECONDS", "5"))
DEFAULT_POLL_TIMEOUT_SECONDS = int(os.getenv("RENDER_POLL_TIMEOUT_SECONDS", "300"))


# ============================================================
# PUBLIC API
# ============================================================

def deploy_system(base_dir: str = ".", validation_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Backward-compatible entrypoint.

    Parameters
    ----------
    base_dir:
        Included for interface compatibility. Not used directly here.
    validation_report:
        Optional validation report. If provided and failed, deployment is blocked.

    Returns
    -------
    Structured deployment result dict.
    """
    if isinstance(validation_report, dict):
        if not validation_report.get("overall_pass", False):
            return _failure(
                error_type="deployment_blocked",
                error_message="Deployment blocked because validation did not pass",
                diagnostics={"stage": "preflight_validation_gate"},
            )

    return trigger_deploy_and_verify()


def trigger_deploy_and_verify() -> Dict[str, Any]:
    """
    Full deployment loop.

    Flow
    ----
    1. Preflight credential check.
    2. Trigger deployment.
    3. Poll service state/live URL.
    4. Probe live /health.
    """
    preflight = _preflight()
    if not preflight["success"]:
        return preflight

    trigger_result = _trigger_deployment()
    if not trigger_result["success"]:
        return trigger_result

    service_result = _poll_for_live_service()
    if not service_result["success"]:
        return service_result

    live_url = service_result["live_url"]

    probe_result = probe_live_url(live_url)
    if not probe_result["success"]:
        return {
            "success": False,
            "deployment_status": "deployed_but_probe_failed",
            "live_url": live_url,
            "error_type": probe_result["error_type"],
            "error_message": probe_result["error_message"],
            "diagnostics": {
                "stage": "live_probe",
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
            "trigger": trigger_result,
            "service_result": service_result,
            "probe_result": probe_result,
        },
    }


def probe_live_url(live_url: str) -> Dict[str, Any]:
    """
    Probe the live service health endpoint deterministically.
    """
    if not isinstance(live_url, str) or not live_url.strip():
        return _failure(
            error_type="live_probe_invalid_url",
            error_message="Live URL is missing or invalid",
            diagnostics={"stage": "probe_live_url"},
        )

    target = live_url.rstrip("/") + DEFAULT_HEALTH_PATH

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
# PREFLIGHT
# ============================================================

def _preflight() -> Dict[str, Any]:
    api_key = os.getenv("RENDER_API_KEY", "").strip()
    service_id = os.getenv("RENDER_SERVICE_ID", "").strip()
    deploy_hook = os.getenv("RENDER_DEPLOY_HOOK_URL", "").strip()

    if deploy_hook:
        return {
            "success": True,
            "mode": "deploy_hook",
            "error_type": None,
            "error_message": None,
            "diagnostics": {"stage": "preflight", "mode": "deploy_hook"},
        }

    if not api_key:
        return _failure(
            error_type="render_unconfigured",
            error_message="RENDER_API_KEY is not set",
            diagnostics={"stage": "preflight", "missing": "RENDER_API_KEY"},
        )

    if not service_id:
        return _failure(
            error_type="render_unconfigured",
            error_message="RENDER_SERVICE_ID is not set",
            diagnostics={"stage": "preflight", "missing": "RENDER_SERVICE_ID"},
        )

    return {
        "success": True,
        "mode": "render_api",
        "error_type": None,
        "error_message": None,
        "diagnostics": {"stage": "preflight", "mode": "render_api"},
    }


# ============================================================
# TRIGGER
# ============================================================

def _trigger_deployment() -> Dict[str, Any]:
    deploy_hook = os.getenv("RENDER_DEPLOY_HOOK_URL", "").strip()

    if deploy_hook:
        return _trigger_via_deploy_hook(deploy_hook)

    return _trigger_via_render_api()


def _trigger_via_deploy_hook(deploy_hook: str) -> Dict[str, Any]:
    try:
        response = requests.post(deploy_hook, timeout=30)
    except Exception as exc:
        return _failure(
            error_type="render_trigger_error",
            error_message=str(exc),
            diagnostics={
                "stage": "trigger_deploy_hook",
                "exception_class": exc.__class__.__name__,
            },
        )

    if response.status_code >= 400:
        return _failure(
            error_type="render_trigger_http_error",
            error_message=f"Deploy hook returned HTTP {response.status_code}",
            diagnostics={
                "stage": "trigger_deploy_hook",
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
            "status_code": response.status_code,
            "response_text": response.text[:1000],
        },
    }


def _trigger_via_render_api() -> Dict[str, Any]:
    api_key = os.getenv("RENDER_API_KEY", "").strip()
    service_id = os.getenv("RENDER_SERVICE_ID", "").strip()

    url = f"{DEFAULT_RENDER_BASE_URL}/services/{service_id}/deploys"
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
            "status_code": response.status_code,
            "payload": payload,
        },
    }


# ============================================================
# POLLING
# ============================================================

def _poll_for_live_service() -> Dict[str, Any]:
    api_key = os.getenv("RENDER_API_KEY", "").strip()
    service_id = os.getenv("RENDER_SERVICE_ID", "").strip()
    deploy_hook = os.getenv("RENDER_DEPLOY_HOOK_URL", "").strip()

    if deploy_hook and (not api_key or not service_id):
        return _failure(
            error_type="render_poll_unconfigured",
            error_message="Polling requires RENDER_API_KEY and RENDER_SERVICE_ID even when using a deploy hook",
            diagnostics={"stage": "poll_preflight"},
        )

    url = f"{DEFAULT_RENDER_BASE_URL}/services/{service_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    deadline = time.time() + DEFAULT_POLL_TIMEOUT_SECONDS
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
                    "payload": payload,
                },
            }

        time.sleep(DEFAULT_POLL_INTERVAL_SECONDS)

    return _failure(
        error_type="render_poll_timeout",
        error_message="Timed out waiting for live Render service URL",
        diagnostics={
            "stage": "poll_service",
            "last_payload": last_payload,
            "timeout_seconds": DEFAULT_POLL_TIMEOUT_SECONDS,
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
    result = trigger_deploy_and_verify()
    print(json.dumps(result, indent=2))
