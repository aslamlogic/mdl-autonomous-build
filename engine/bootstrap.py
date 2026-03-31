import os
import sys
import json
import requests
from pathlib import Path

API_URL = "https://api.openai.com/v1/responses"
ENGINE_SPEC_PATH = "specs/engine.json"
APP_SPEC_PATH = "specs/init.json"


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
    engine_exists = Path(ENGINE_SPEC_PATH).exists()
    app_exists = Path(APP_SPEC_PATH).exists()

    if engine_exists:
        return "engine", ENGINE_SPEC_PATH, read_json_file(ENGINE_SPEC_PATH)

    if app_exists:
        return "app", APP_SPEC_PATH, read_json_file(APP_SPEC_PATH)

    fail("No spec found. Expected specs/engine.json or specs/init.json.")


def build_prompt(mode: str, spec_path: str, spec: dict) -> str:
    if mode == "engine":
        return f"""You are an expert software engineer.

Generate files that UPGRADE OR REPLACE THE SOFTWARE FACTORY ENGINE ITSELF.

Return ONLY valid JSON in this exact format:

{{
  "files": [
    {{
      "path": "path/to/file",
      "content": "file content"
    }}
  ]
}}

STRICT RULES:
1. Output ONLY JSON
2. Generate complete file contents
3. Files must be syntactically valid
4. Preserve a GitHub Actions + OpenAI bootstrap architecture
5. The engine must remain able to:
   - read specs
   - call OpenAI
   - write files
   - commit generated files
6. Include engine/bootstrap.py if the engine is being changed
7. Use safe relative file paths only
8. Do not include markdown fences

CURRENT MODE: ENGINE SELF-EVOLUTION
SOURCE SPEC PATH: {spec_path}

ENGINE SPEC:
{json.dumps(spec, ensure_ascii=False)}
"""
    return f"""You are an expert software engineer.

Generate a COMPLETE, runnable software project from the supplied application specification.

Return ONLY valid JSON in this exact format:

{{
  "files": [
    {{
      "path": "path/to/file",
      "content": "file content"
    }}
  ]
}}

STRICT RULES:
1. Output ONLY JSON
2. Generate MULTIPLE files (minimum 5 unless the spec clearly demands fewer)
3. Use proper project structure
4. All files must be complete and syntactically valid
5. Use safe relative file paths only
6. Do not include markdown fences

CURRENT MODE: APPLICATION BUILD
SOURCE SPEC PATH: {spec_path}

APPLICATION SPEC:
{json.dumps(spec, ensure_ascii=False)}
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
                {
                    "role": "system",
                    "content": "Return only valid JSON. No commentary."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        },
        timeout=120
    )

    if response.status_code != 200:
        fail(f"OpenAI API error: {response.text}")

    data = response.json()

    try:
        text = data["output"][0]["content"][0]["text"]
    except Exception:
        fail("Unexpected OpenAI response format")

    print("===== OPENAI RAW OUTPUT =====")
    print(text)
    print("===== END OUTPUT =====")

    try:
        return json.loads(text)
    except Exception as e:
        fail(f"Failed to parse JSON from model output: {e}")


def validate_file_entry(file_entry: dict) -> tuple[str, str]:
    path = file_entry.get("path")
    content = file_entry.get("content")

    if not path or not isinstance(content, str):
        fail("Invalid file entry")

    safe_path = os.path.normpath(path)

    if safe_path.startswith("..") or os.path.isabs(safe_path):
        fail(f"Unsafe file path: {path}")

    return safe_path, content


def write_files(files: list[dict]) -> None:
    for file_entry in files:
        safe_path, content = validate_file_entry(file_entry)

        os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)

        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✓ Wrote: {safe_path}")


def main():
    mode, spec_path, spec = select_mode_and_spec()
    print(f"===== MODE =====")
    print(mode)
    print(f"===== SPEC =====")
    print(spec_path)

    prompt = build_prompt(mode, spec_path, spec)
    result = call_openai(prompt)

    files = result.get("files")
    if not isinstance(files, list) or not files:
        fail("No files returned")

    write_files(files)


if __name__ == "__main__":
    main()
