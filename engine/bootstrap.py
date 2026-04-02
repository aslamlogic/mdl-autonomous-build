import json
import os
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import requests

CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"

SPEC_CANDIDATES = [
    Path("specs/app.json"),
    Path("specs/init.json"),
]

GOAL_PATH = Path("goal.json")
QUEUE_PATH = Path("tasks/queue.json")
STATE_PATH = Path("tasks/state.json")

FORBIDDEN_PREFIXES = (
    ".git/",
    ".github/workflows/",
)

SUPPORTED_TASKS = {
    "strengthen_contract": "Convert spec to typed contract",
    "add_post_echo": "Add typed POST /echo endpoint",
}

PLANNER_SCHEMA = {
    "name": "task_plan",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": list(SUPPORTED_TASKS.keys()),
                },
            }
        },
        "required": ["tasks"],
    },
}

OUTPUT_SCHEMA = {
    "name": "generated_files",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "minItems": 2,
                "items": {
                    "type": "object",
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


def fail(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)


def read_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def read_spec():
    for p in SPEC_CANDIDATES:
        if p.exists():
            return p, json.loads(p.read_text())
    fail("No spec found")


def save_spec(path, spec):
    path.write_text(json.dumps(spec, indent=2))


# ---------------- TASK LOGIC ---------------- #

def to_contract(spec):
    if "api" in spec:
        return spec

    endpoints = spec.get("endpoints", [])
    new_eps = []

    for ep in endpoints:
        resp = ep.get("response", {})
        schema = {
            k: {"type": "string", "example": v}
            for k, v in resp.items()
        }

        new_eps.append({
            "name": ep.get("name", "endpoint"),
            "method": ep.get("method", "GET"),
            "path": ep.get("path", "/"),
            "response": {
                "type": "object",
                "schema": schema
            }
        })

    return {
        "system": {"name": "meta", "type": "fastapi"},
        "api": {"endpoints": new_eps}
    }


def add_post_echo(spec):
    spec = to_contract(spec)
    eps = spec["api"]["endpoints"]

    if any(e["path"] == "/echo" for e in eps):
        return spec

    eps.append({
        "name": "echo",
        "method": "POST",
        "path": "/echo",
        "request": {
            "type": "object",
            "schema": {
                "text": {"type": "string", "example": "hello"}
            }
        },
        "response": {
            "type": "object",
            "schema": {
                "echo": {"type": "string", "example": "hello"}
            }
        }
    })
    return spec


def apply_task(spec, task):
    if task == "strengthen_contract":
        return to_contract(spec)
    if task == "add_post_echo":
        return add_post_echo(spec)
    fail(f"Unknown task {task}")


# ---------------- GENERATION ---------------- #

def build_messages(spec):
    return [
        {
            "role": "system",
            "content": (
                "You MUST output EXACTLY two files:\n"
                "main.py and requirements.txt\n\n"
                "No markdown. No explanation.\n"
                "Return valid JSON only.\n\n"
                "requirements.txt MUST contain:\n"
                "fastapi\nuvicorn\npydantic\n"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(spec, indent=2),
        },
    ]


def call_openai(messages):
    r = requests.post(
        CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
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
    )

    if r.status_code != 200:
        fail(r.text)

    content = r.json()["choices"][0]["message"]["content"]
    return json.loads(content)


# ---------------- VALIDATION ---------------- #

def validate(payload):
    files = payload.get("files", [])
    paths = [f["path"] for f in files]

    if "main.py" not in paths:
        fail("main.py missing")

    if "requirements.txt" not in paths:
        fail("requirements.txt missing")

    main = next(f["content"] for f in files if f["path"] == "main.py")

    if "FastAPI" not in main:
        fail("FastAPI missing")

    if "@app.get" not in main:
        fail("GET missing")

    if "POST" in main and "@app.post" not in main:
        fail("POST missing")


def write_files(payload):
    for f in payload["files"]:
        path = Path(f["path"])
        content = f["content"].strip()

        if "```" in content:
            fail("markdown detected")

        path.write_text(content + "\n")
        print(f"WROTE {path}")


# ---------------- MAIN LOOP ---------------- #

def main():
    spec_path, spec = read_spec()
    goal = read_json(GOAL_PATH, {}).get("goal", "")

    queue = read_json(QUEUE_PATH, {"tasks": []})
    state = read_json(STATE_PATH, {"current": 0})

    if not queue["tasks"]:
        tasks = []
        if "post" in goal.lower():
            tasks.append("add_post_echo")
        tasks.append("strengthen_contract")

        queue = {"tasks": tasks}
        write_json(QUEUE_PATH, queue)

    idx = state.get("current", 0)

    if idx < len(queue["tasks"]):
        task = queue["tasks"][idx]
        print(f"APPLYING TASK: {task}")

        spec = apply_task(spec, task)
        save_spec(spec_path, spec)

        payload = call_openai(build_messages(spec))
        validate(payload)
        write_files(payload)

        state["current"] = idx + 1
        write_json(STATE_PATH, state)

    print("BOOTSTRAP COMPLETE")


if __name__ == "__main__":
    main()
