
import json
import os
from typing import Any, Dict, List

from openai import OpenAI


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _system_message() -> str:
    return """
You are a deterministic multi-file repair engine.

HARD RULES:
1. Return only strict JSON.
2. JSON schema:
   {
     "files": [
       {"path": "<allowed path>", "content": "<full file content>"}
     ]
   }
3. Only create or modify files listed in allowed_files.
4. Do not emit markdown fences.
5. Do not emit explanations.
6. Prefer the minimum changes needed to satisfy the repair contract.
7. If a file is not required for repair, do not include it.
"""


def _user_message(
    spec_text: str,
    repair_contract: List[Dict[str, Any]],
    allowed_files: List[str],
) -> str:
    return f"""
BASE_SPEC:
{spec_text}

ALLOWED_FILES:
{json.dumps(allowed_files, indent=2)}

REPAIR_CONTRACT:
{json.dumps(repair_contract, indent=2)}

OUTPUT:
Return strict JSON only.
"""


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    return cleaned


def _validate_payload(payload: Dict[str, Any], allowed_files: List[str]) -> Dict[str, str]:
    files = payload.get("files")
    if not isinstance(files, list):
        raise RuntimeError("LLM payload missing files list")

    result: Dict[str, str] = {}
    for item in files:
        if not isinstance(item, dict):
            raise RuntimeError("LLM payload file entry is not an object")

        path = item.get("path")
        content = item.get("content")

        if not isinstance(path, str) or not path:
            raise RuntimeError("LLM payload file path is invalid")
        if path not in allowed_files:
            raise RuntimeError(f"LLM attempted forbidden file path: {path}")
        if not isinstance(content, str):
            raise RuntimeError(f"LLM payload content invalid for: {path}")

        result[path] = content

    return result


def generate(
    spec_text: str,
    repair_contract: List[Dict[str, Any]],
    allowed_files: List[str],
) -> Dict[str, str]:
    client = _get_client()

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        messages=[
            {"role": "system", "content": _system_message()},
            {"role": "user", "content": _user_message(spec_text, repair_contract, allowed_files)},
        ],
    )

    content = response.choices[0].message.content
    if not content or not isinstance(content, str):
        raise RuntimeError("LLM returned empty content")

    cleaned = _strip_fences(content)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM did not return valid JSON: {e}") from e

    return _validate_payload(payload, allowed_files)
