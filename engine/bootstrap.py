import os
import sys
import json
import re
import requests

API_URL = "https://api.anthropic.com/v1/messages"


def fail(msg):
    print(msg)
    sys.exit(1)


def extract_json(text):
    text = text.strip()

    try:
        return json.loads(text)
    except:
        pass

    blocks = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    for b in blocks:
        try:
            return json.loads(b.strip())
        except:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except:
            pass

    return None


def call_claude(prompt):
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        fail("ERROR: CLAUDE_API_KEY not set")

    response = requests.post(
        API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-3-haiku-20240307",
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=60
    )

    if response.status_code != 200:
        fail(f"Claude API error: {response.text}")

    try:
        data = response.json()
    except Exception as e:
        fail(f"Invalid JSON response: {e}")

    try:
        content = data["content"]
        text = ""
        for block in content:
            if isinstance(block, dict) and "text" in block:
                text += block["text"]
    except Exception:
        fail("Unexpected Anthropic response format")

    print("===== CLAUDE RAW OUTPUT =====")
    print(text)
    print("===== END OUTPUT =====")

    parsed = extract_json(text)

    if not parsed:
        fail("Failed to parse JSON from Claude output")

    return parsed


def main():
    try:
        with open("specs/init.json", "r") as f:
            spec = json.load(f)
    except Exception as e:
        fail(f"Spec load error: {e}")

    prompt = f"""You are an expert software engineer.

Return ONLY valid JSON in this structure:

{{
  "files": [
    {{
      "path": "main.py",
      "content": "code"
    }}
  ]
}}

Specification:
{json.dumps(spec)}
"""

    result = call_claude(prompt)

    files = result.get("files")
    if not isinstance(files, list) or not files:
        fail("No files returned")

    for file in files:
        path = file.get("path")
        content = file.get("content")

        if not path or not isinstance(content, str):
            fail("Invalid file entry")

        safe_path = os.path.normpath(path)

        if safe_path.startswith("..") or os.path.isabs(safe_path):
            fail("Unsafe file path")

        os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)

        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✓ Wrote: {safe_path}")


if __name__ == "__main__":
    main()
