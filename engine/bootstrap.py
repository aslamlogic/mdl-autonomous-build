import os
import sys
import json
import requests
from pathlib import Path

API_URL = "https://api.openai.com/v1/responses"
ENGINE_SPEC_PATH = "specs/engine.json"
APP_SPEC_PATH = "specs/init.json"

FORBIDDEN_PREFIXES = [
    ".github/workflows/"
]


def fail(msg: str) -> None:
    print(msg)
    sys.exit(1)


def read_json_file(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        fail(f"Spec load error ({path}): {e}")


def select_mode_and_spec():
    if Path(ENGINE_SPEC_PATH).exists():
        return "engine", ENGINE_SPEC_PATH, read_json_file(ENGINE_SPEC_PATH)

    if Path(APP_SPEC_PATH).exists():
        return "app", APP_SPEC_PATH, read_json_file(APP_SPEC_PATH)

    fail("No spec found.")


def build_prompt(mode: str, spec_path: str, spec: dict) -> str:
    if mode == "engine":
        return f"""You are an expert software engineer.

Generate files that upgrade the engine.

Return ONLY JSON:

{{
  "files": [
    {{
      "path": "path/to/file",
      "content": "file content"
    }}
  ]
}}

DO NOT generate any files under .github/workflows/

Specification:
{json.dumps(spec)}
"""
    return f"""Generate application files.

Return ONLY JSON:

{{
  "files": [
    {{
      "path": "path/to/file",
      "content": "file content"
    }}
  ]
}}

Specification:
{json.dumps(spec)}
"""


def call_openai(prompt: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        fail("ERROR: OPENAI_API_KEY not set")

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-5.4-mini",
            "input": [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=120,
    )

    if response.status_code != 200:
        fail(f"OpenAI API error: {response.text}")

    data = response.json()

    try:
        text = data["output"][0]["content"][0]["text"]
    except Exception:
        fail("Unexpected response format")

    print("===== OPENAI RAW OUTPUT =====")
    print(text)
    print("===== END OUTPUT =====")

    try:
        return json.loads(text)
    except Exception as e:
        fail(f"JSON parse error: {e}")


def is_forbidden(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)


def write_files(files: list[dict]) -> None:
    for f in files:
        path = f.get("path")
        content = f.get("content")

        if not path or not isinstance(content, str):
            fail("Invalid file entry")

        if is_forbidden(path):
            print(f"⛔ Skipped forbidden path: {path}")
            continue

        safe_path = os.path.normpath(path)

        if safe_path.startswith("..") or os.path.isabs(safe_path):
            fail(f"Unsafe path: {path}")

        os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)

        with open(safe_path, "w", encoding="utf-8") as out:
            out.write(content)

        print(f"✓ Wrote: {safe_path}")


def main():
    mode, spec_path, spec = select_mode_and_spec()

    print("===== MODE =====")
    print(mode)

    prompt = build_prompt(mode, spec_path, spec)
    result = call_openai(prompt)

    files = result.get("files")
    if not isinstance(files, list) or not files:
        fail("No files returned")

    write_files(files)


if __name__ == "__main__":
    main()
