import json
import os
import sys
from pathlib import Path

import requests

CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"

SPEC_PATH = Path("specs/init.json")
GOAL_PATH = Path("goal.json")
QUEUE_PATH = Path("tasks/queue.json")
STATE_PATH = Path("tasks/state.json")

OUTPUT_SCHEMA = {
    "name": "generated_files",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "files": {
                "type": "array",
                "minItems": 2,
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


def fail(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_spec() -> dict:
    if not SPEC_PATH.exists():
        fail("Spec missing")
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def save_spec(spec: dict) -> None:
    SPEC_PATH.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")


def to_contract(spec: dict) -> dict:
    if "api" in spec:
        return spec

    eps = spec.get("endpoints", [])
    new_eps = []

    for ep in eps:
        response_schema = {}
        for k, v in ep.get("response", {}).items():
            inferred_type = "string"
            if isinstance(v, bool):
                inferred_type = "boolean"
            elif isinstance(v, int):
                inferred_type = "integer"
            elif isinstance(v, float):
                inferred_type = "number"
            elif isinstance(v, list):
                inferred_type = "array"
            elif isinstance(v, dict):
                inferred_type = "object"

            response_schema[k] = {"type": inferred_type, "example": v}

        new_eps.append(
            {
                "name": ep.get("name", "endpoint"),
                "method": ep.get("method", "GET"),
                "path": ep.get("path", "/"),
                "response": {
                    "type": "object",
                    "schema": response_schema,
                },
            }
        )

    return {
        "system": {"name": "meta", "type": "fastapi"},
        "api": {"endpoints": new_eps},
    }


def add_post_echo(spec: dict) -> dict:
    spec = to_contract(spec)

    if any(e.get("path") == "/echo" for e in spec["api"]["endpoints"]):
        return spec

    spec["api"]["endpoints"].append(
        {
            "name": "echo",
            "method": "POST",
            "path": "/echo",
            "request": {
                "type": "object",
                "schema": {
                    "text": {"type": "string", "example": "hello"}
                },
            },
            "response": {
                "type": "object",
                "schema": {
                    "echo": {"type": "string", "example": "hello"}
                },
            },
        }
    )
    return spec


def apply_task(spec: dict, task: str) -> dict:
    if task == "add_post_echo":
        return add_post_echo(spec)
    if task == "strengthen_contract":
        return to_contract(spec)
    fail(f"Unknown task {task}")
    return spec


def build_messages(spec: dict) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "Return ONLY valid JSON matching the schema. "
                "Generate EXACTLY two files: main.py and requirements.txt. "
                "No markdown. No commentary."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(spec),
        },
    ]


def call_openai(spec: dict) -> dict:
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
            "messages": build_messages(spec),
            "response_format": {
                "type": "json_schema",
                "json_schema": OUTPUT_SCHEMA,
            },
            "temperature": 0,
        },
        timeout=180,
    )

    if response.status_code != 200:
        fail(response.text)

    try:
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        fail(f"Invalid model response: {exc}")
        return {}


def validate(payload: dict) -> None:
    files = payload.get("files", [])
    paths = [f.get("path") for f in files]

    if "main.py" not in paths:
        fail("main.py missing")

    if "requirements.txt" not in paths:
        fail("requirements.txt missing")


def write_files(payload: dict) -> None:
    for f in payload["files"]:
        path = Path(f["path"])
        content = f["content"].strip()

        if "```" in content:
            fail(f"markdown detected in {f['path']}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        print(f"WROTE {f['path']}")


def initialise_queue_if_needed(goal: str, queue: dict) -> dict:
    tasks = queue.get("tasks", [])
    if tasks:
        return queue

    planned = []
    if "post" in goal.lower():
        planned.append("add_post_echo")
    planned.append("strengthen_contract")

    queue = {"tasks": planned}
    write_json(QUEUE_PATH, queue)
    return queue


def main() -> None:
    spec = read_spec()
    goal = read_json(GOAL_PATH, {}).get("goal", "")
    queue = read_json(QUEUE_PATH, {"tasks": []})
    state = read_json(STATE_PATH, {"index": 0, "completed": []})

    if "index" not in state:
        state["index"] = 0
    if "completed" not in state:
        state["completed"] = []

    queue = initialise_queue_if_needed(goal, queue)

    tasks = queue["tasks"]
    idx = state["index"]

    while idx < len(tasks):
        task = tasks[idx]

        if task in state["completed"]:
            state["index"] = idx + 1
            write_json(STATE_PATH, state)
            idx = state["index"]
            continue

        print(f"APPLYING TASK: {task}")

        spec = apply_task(spec, task)
        save_spec(spec)

        payload = call_openai(spec)
        validate(payload)
        write_files(payload)

        state["completed"].append(task)
        state["index"] = idx + 1
        write_json(STATE_PATH, state)

        idx = state["index"]

    if state["index"] >= len(tasks):
        print("ALL TASKS COMPLETE")
        return

    fail("Loop terminated before all tasks completed")


if __name__ == "__main__":
    main()
