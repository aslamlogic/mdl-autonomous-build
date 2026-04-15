"""
engine/llm_interface.py

Deterministic LLM interface for the Meta Dev Launcher.

Purpose
-------
1. Build a strict, multi-file code bundle from a governed prompt.
2. Support multi-endpoint FastAPI generation.
3. Enforce a machine-readable file contract before any write stage.
4. Return structured diagnostics instead of ambiguous raw text.

Design notes
------------
- This file is deliberately provider-agnostic at the orchestration layer.
- It supports OpenAI-compatible chat completions when the required
  environment variables are present.
- If no provider is configured, it returns a structured failure object
  instead of crashing.
- The output contract is a JSON object of the form:

    {
      "files": [
        {"path": "generated_app/main.py", "content": "..."},
        {"path": "generated_app/__init__.py", "content": "..."}
      ]
    }

- The interface also tolerates fenced JSON or raw text surrounding the JSON
  and extracts the first valid JSON object it can parse.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


# ============================================================
# CONFIG
# ============================================================

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-thinking")
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0"))
DEFAULT_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "16000"))

SYSTEM_PROMPT = """
You are a deterministic software generation engine.

Return ONLY a single JSON object.
Do not return markdown fences.
Do not return commentary.
Do not explain your choices.

Required output shape:
{
  "files": [
    {
      "path": "relative/path/to/file.py",
      "content": "full file contents here"
    }
  ]
}

Requirements:
1. Generate a complete runnable FastAPI application.
2. Implement every endpoint defined in the specification.
3. Include required package/module files such as __init__.py where needed.
4. Use stable imports.
5. Ensure /health exists and returns a JSON object.
6. Do not omit required files.
7. Do not include placeholder text.
8. Output must be valid JSON.
""".strip()


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class GenerationResult:
    success: bool
    files: List[Dict[str, str]]
    raw_text: str
    provider: str
    model: str
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    diagnostics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "files": self.files,
            "raw_text": self.raw_text,
            "provider": self.provider,
            "model": self.model,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "diagnostics": self.diagnostics or {},
        }


# ============================================================
# PUBLIC API
# ============================================================

def generate_code(prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Backward-compatible entrypoint used by existing controller flows.

    Input
    -----
    prompt: Final assembled generation payload as a string.
    model: Optional provider model override.

    Returns
    -------
    Dict[str, Any] with:
    - success
    - files
    - raw_text
    - provider
    - model
    - error_type
    - error_message
    - diagnostics
    """
    result = generate_candidate_code_bundle(prompt=prompt, model=model)
    return result.to_dict()


def generate_candidate_code_bundle(prompt: str, model: Optional[str] = None) -> GenerationResult:
    """
    Main generation orchestration method.

    Flow
    ----
    1. Call provider.
    2. Extract JSON bundle.
    3. Validate bundle structure.
    4. Normalize files.
    5. Enforce minimal contract.
    """
    selected_model = model or DEFAULT_MODEL

    provider_result = _call_provider(prompt=prompt, model=selected_model)
    if not provider_result["success"]:
        return GenerationResult(
            success=False,
            files=[],
            raw_text=provider_result.get("raw_text", ""),
            provider=provider_result.get("provider", "unconfigured"),
            model=selected_model,
            error_type=provider_result.get("error_type", "generation_failure"),
            error_message=provider_result.get("error_message", "Unknown provider error"),
            diagnostics=provider_result.get("diagnostics", {}),
        )

    raw_text = provider_result["raw_text"]

    parsed_bundle, parse_error = _extract_file_bundle(raw_text)
    if parse_error is not None:
        return GenerationResult(
            success=False,
            files=[],
            raw_text=raw_text,
            provider=provider_result["provider"],
            model=selected_model,
            error_type="malformed_file_bundle",
            error_message=parse_error,
            diagnostics={"stage": "bundle_parse"},
        )

    normalized_files, normalization_error = _normalize_bundle(parsed_bundle)
    if normalization_error is not None:
        return GenerationResult(
            success=False,
            files=[],
            raw_text=raw_text,
            provider=provider_result["provider"],
            model=selected_model,
            error_type="bundle_contract_failure",
            error_message=normalization_error,
            diagnostics={"stage": "bundle_normalize"},
        )

    contract_error = _validate_minimal_contract(normalized_files)
    if contract_error is not None:
        return GenerationResult(
            success=False,
            files=[],
            raw_text=raw_text,
            provider=provider_result["provider"],
            model=selected_model,
            error_type="bundle_contract_failure",
            error_message=contract_error,
            diagnostics={"stage": "bundle_contract"},
        )

    return GenerationResult(
        success=True,
        files=normalized_files,
        raw_text=raw_text,
        provider=provider_result["provider"],
        model=selected_model,
        diagnostics={
            "file_count": len(normalized_files),
            "paths": [item["path"] for item in normalized_files],
        },
    )


# ============================================================
# PROVIDER LAYER
# ============================================================

def _call_provider(prompt: str, model: str) -> Dict[str, Any]:
    """
    Calls configured LLM provider.

    Current implementation:
    - OpenAI-compatible via OPENAI_API_KEY
    - Safe structured failure if provider is unavailable
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {
            "success": False,
            "provider": "unconfigured",
            "raw_text": "",
            "error_type": "generation_unconfigured",
            "error_message": "OPENAI_API_KEY is not set",
            "diagnostics": {"env_var_missing": "OPENAI_API_KEY"},
        }

    if OpenAI is None:
        return {
            "success": False,
            "provider": "openai",
            "raw_text": "",
            "error_type": "provider_import_failure",
            "error_message": "openai package is not available",
            "diagnostics": {},
        }

    try:
        client = OpenAI(api_key=api_key)

        completion = client.chat.completions.create(
            model=model,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=DEFAULT_MAX_TOKENS,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        message = completion.choices[0].message
        raw_text = message.content if message and message.content else ""

        if not raw_text.strip():
            return {
                "success": False,
                "provider": "openai",
                "raw_text": raw_text,
                "error_type": "generation_empty",
                "error_message": "Provider returned an empty response",
                "diagnostics": {},
            }

        return {
            "success": True,
            "provider": "openai",
            "raw_text": raw_text,
            "diagnostics": {},
        }

    except Exception as exc:
        return {
            "success": False,
            "provider": "openai",
            "raw_text": "",
            "error_type": "generation_provider_error",
            "error_message": str(exc),
            "diagnostics": {"exception_class": exc.__class__.__name__},
        }


# ============================================================
# BUNDLE EXTRACTION
# ============================================================

def _extract_file_bundle(raw_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Extract the first valid JSON object from raw provider output.

    Handles:
    - pure JSON
    - fenced JSON
    - stray prose before/after JSON
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None, "Raw provider output is empty"

    stripped = raw_text.strip()

    # 1. Direct parse
    try:
        obj = json.loads(stripped)
        return obj, None
    except Exception:
        pass

    # 2. Remove fenced code blocks if present
    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, flags=re.DOTALL)
    if fenced_match:
        candidate = fenced_match.group(1)
        try:
            obj = json.loads(candidate)
            return obj, None
        except Exception:
            pass

    # 3. Extract first balanced JSON object from text
    candidate = _extract_first_balanced_json_object(stripped)
    if candidate:
        try:
            obj = json.loads(candidate)
            return obj, None
        except Exception as exc:
            return None, f"Found probable JSON object but failed to parse: {exc}"

    return None, "No valid JSON object could be extracted from provider output"


def _extract_first_balanced_json_object(text: str) -> Optional[str]:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for idx in range(start, len(text)):
        ch = text[idx]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]

    return None


# ============================================================
# BUNDLE NORMALIZATION
# ============================================================

def _normalize_bundle(bundle: Dict[str, Any]) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """
    Normalize output bundle to:
    [
      {"path": "...", "content": "..."},
      ...
    ]
    """
    if not isinstance(bundle, dict):
        return [], "Bundle root must be a JSON object"

    files = bundle.get("files")
    if not isinstance(files, list):
        return [], "Bundle must contain a 'files' array"

    normalized: List[Dict[str, str]] = []

    for index, item in enumerate(files):
        if not isinstance(item, dict):
            return [], f"files[{index}] must be an object"

        path = item.get("path")
        content = item.get("content")

        if not isinstance(path, str) or not path.strip():
            return [], f"files[{index}].path must be a non-empty string"

        if not isinstance(content, str):
            return [], f"files[{index}].content must be a string"

        normalized.append(
            {
                "path": _normalize_relative_path(path),
                "content": content,
            }
        )

    normalized = _deduplicate_by_path_last_write_wins(normalized)
    return normalized, None


def _normalize_relative_path(path: str) -> str:
    path = path.strip().replace("\\", "/")
    path = re.sub(r"/+", "/", path)
    path = path.lstrip("/")
    return path


def _deduplicate_by_path_last_write_wins(files: List[Dict[str, str]]) -> List[Dict[str, str]]:
    latest: Dict[str, Dict[str, str]] = {}
    order: List[str] = []

    for item in files:
        path = item["path"]
        if path not in latest:
            order.append(path)
        latest[path] = item

    return [latest[path] for path in order]


# ============================================================
# CONTRACT VALIDATION
# ============================================================

def _validate_minimal_contract(files: List[Dict[str, str]]) -> Optional[str]:
    """
    Minimal deterministic bundle checks.

    These are intentionally conservative:
    - at least one Python file
    - main app file present
    - __init__.py present somewhere if package structure is used
    - file paths must be relative and safe
    - no empty contents
    """
    if not files:
        return "Bundle contains no files"

    paths = [item["path"] for item in files]

    for item in files:
        path = item["path"]
        content = item["content"]

        if _is_forbidden_path(path):
            return f"Forbidden file path: {path}"

        if not content.strip():
            return f"File content is empty for path: {path}"

    python_files = [p for p in paths if p.endswith(".py")]
    if not python_files:
        return "Bundle must contain at least one Python file"

    if not _contains_main_app_file(paths):
        return "Bundle must contain an application entry file such as generated_app/main.py or app/main.py"

    if _uses_package_structure(paths) and not any(p.endswith("__init__.py") for p in paths):
        return "Bundle uses package structure but contains no __init__.py file"

    return None


def _is_forbidden_path(path: str) -> bool:
    if path.startswith("../") or "/../" in path or path == "..":
        return True
    if path.startswith(".git/") or "/.git/" in path:
        return True
    if path.startswith("/"):
        return True
    return False


def _contains_main_app_file(paths: List[str]) -> bool:
    accepted = {
        "generated_app/main.py",
        "app/main.py",
        "src/main.py",
        "main.py",
    }
    return any(path in accepted for path in paths)


def _uses_package_structure(paths: List[str]) -> bool:
    """
    If any file is nested in a python package-like directory, treat as package structure.
    """
    for path in paths:
        if path.endswith(".py") and "/" in path:
            return True
    return False
