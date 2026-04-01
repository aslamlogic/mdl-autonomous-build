import json
import os
import re
import sys
from pathlib import Path

import requests

CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
SPEC_CANDIDATES = [
    Path("specs/app.json"),
    Path("specs/init.json"),
]
FORBIDDEN_PREFIXES = (
    ".git/",
    ".github/workflows/",
)

OUTPUT_SCHEMA = {
    "name": "generated_files",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "files": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            }
        },
        "required": ["files"],
    },
}


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    sys.exit(1)


def read_spec() -> tuple[Path, dict]:
    for path in SPEC_CANDIDATES:
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                return path, json.load(handle)
    fail("No spec found. Expected specs/app.json or specs/init.json.")


def build_messages(spec_path: Path, spec: dict) -> list[dict]:
    developer_text = (
        "You are a deterministic software file generator. "
        "Return only JSON matching the supplied schema. "
        "Do not include markdown fences. "
        "Do not include commentary. "
        "Generate complete file contents only."
    )

    user_text = (
        f"Specification source: {spec_path.as_posix()}\n"
        "Generate a minimal, runnable FastAPI application from this specification.\n"
        "Rules:\n"
        "1. Return only files.\n"
        "2. Do not generate .github/workflows files.\n"
        "3. Keep output minimal and executable.\n"
        "4. If requirements.txt is needed, include only necessary packages.\n"
        "5. Main entrypoint must be main.py.\n"
        "6. The service must expose exactly the endpoints defined in the spec.\n"
        "7. Use plain Python and FastAPI only.\n\n"
        f"SPEC:\n{json.dumps(spec, indent=2, ensure_ascii=False)}"
    )

    return [
        {"role": "developer", "content": developer_text},
        {"role": "user", "content": user_text},
    ]


def call_openai(messages: list[dict]) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        fail("OPENAI_API_KEY is not set.")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    response = requests.post(
        CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": OUTPUT_SCHEMA,
            },
            "temperature": 0,
        },
        timeout=180,
    )

    if response.status_code != 200:
        fail(f"OpenAI API call failed: {response.status_code} {response.text}")

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as exc:
        fail(f"Unexpected OpenAI response format: {exc}")

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        fail(f"Model returned invalid JSON: {exc}\nRaw content:\n{content}")


def normalise_content(content: str) -> str:
    content = content.strip()

    fenced_match = re.fullmatch(r"```[a-zA-Z0-9_-]*\n(.*)\n```", content, flags=re.DOTALL)
    if fenced_match:
        content = fenced_match.group(1)

    if "```" in content:
        fail("Generated content still contains markdown fences.")

    return content


def validate_path(path_str: str) -> Path:
    if not path_str or not isinstance(path_str, str):
        fail("File path is missing or invalid.")

    if any(path_str.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        fail(f"Forbidden output path: {path_str}")

    path = Path(path_str)

    if path.is_absolute():
        fail(f"Absolute paths are not allowed: {path_str}")

    resolved = path.as_posix()
    if resolved.startswith("../") or "/../" in resolved or resolved == "..":
        fail(f"Path traversal is not allowed: {path_str}")

    return path


def write_files(payload: dict) -> None:
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        fail("No files returned.")

    for item in files:
        if not isinstance(item, dict):
            fail("Each file entry must be an object.")

        raw_path = item.get("path")
        raw_content = item.get("content")

        if not isinstance(raw_content, str):
            fail(f"Invalid content for file: {raw_path}")

        output_path = validate_path(raw_path)
        content = normalise_content(raw_content)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        print(f"WROTE {output_path.as_posix()}")


def main() -> None:
    spec_path, spec = read_spec()
    print(f"USING SPEC {spec_path.as_posix()}")
    messages = build_messages(spec_path, spec)
    payload = call_openai(messages)
    write_files(payload)
    print("BOOTSTRAP COMPLETE")


if __name__ == "__main__":
    main()
