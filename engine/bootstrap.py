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


def read_spec():
    for path in SPEC_CANDIDATES:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return path, json.load(f)
    fail("No spec found")


def build_messages(spec_path, spec):
    return [
        {
            "role": "developer",
            "content": (
                "You are a deterministic FastAPI generator.\n"
                "Return ONLY JSON matching the schema.\n"
                "No markdown. No commentary.\n"
                "\n"
                "Requirements:\n"
                "- Build a FastAPI app\n"
                "- Use api.endpoints from spec\n"
                "- Each endpoint must exist\n"
                "- Responses must use schema.example values\n"
                "- Output complete runnable files\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Specification:\n{json.dumps(spec, indent=2)}\n\n"
                "Generate:\n"
                "- main.py\n"
                "- requirements.txt\n"
                "\n"
                "Rules:\n"
                "- Use FastAPI\n"
                "- Implement all endpoints\n"
                "- Return JSON responses based on schema\n"
            ),
        },
    ]


def call_openai(messages):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        fail("OPENAI_API_KEY not set")

    response = requests.post(
        CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
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
        fail(f"OpenAI error: {response.text}")

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        fail(f"Invalid JSON from model: {e}")


def normalise_content(content: str) -> str:
    content = content.strip()

    fenced = re.fullmatch(r"```[a-zA-Z]*\n(.*)\n```", content, re.DOTALL)
    if fenced:
        content = fenced.group(1)

    if "```" in content:
        fail("Markdown fence detected")

    return content


def validate_files(payload):
    files = payload.get("files")

    if not isinstance(files, list) or not files:
        fail("Validation failed: no files returned")

    for item in files:
        path = item.get("path")
        content = item.get("content")

        if not path or not isinstance(path, str):
            fail("Validation failed: invalid path")

        if not content or not isinstance(content, str):
            fail(f"Validation failed: empty content in {path}")

        if "```" in content:
            fail(f"Validation failed: markdown in {path}")

        if len(content.strip()) < 10:
            fail(f"Validation failed: content too short in {path}")

        if path.endswith(".py"):
            if "FastAPI" not in content:
                fail(f"Validation failed: FastAPI missing in {path}")

            if "app = FastAPI()" not in content:
                fail(f"Validation failed: app instance missing in {path}")

            if "@app.get" not in content:
                fail(f"Validation failed: no endpoints in {path}")


def validate_path(path_str: str) -> Path:
    if any(path_str.startswith(p) for p in FORBIDDEN_PREFIXES):
        fail(f"Forbidden path: {path_str}")

    path = Path(path_str)

    if path.is_absolute():
        fail("Absolute paths not allowed")

    if ".." in path.parts:
        fail("Path traversal detected")

    return path


def write_files(payload):
    for item in payload["files"]:
        path = validate_path(item["path"])
        content = normalise_content(item["content"])

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        print(f"WROTE {path}")


def main():
    spec_path, spec = read_spec()
    print(f"USING SPEC {spec_path}")

    messages = build_messages(spec_path, spec)

    payload = call_openai(messages)

    validate_files(payload)

    write_files(payload)

    print("BOOTSTRAP COMPLETE")


if __name__ == "__main__":
    main()
