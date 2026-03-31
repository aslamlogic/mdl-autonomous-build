import os
import sys
import json
import requests

API_URL = "https://api.openai.com/v1/responses"


def fail(msg):
    print(msg)
    sys.exit(1)


def call_openai(prompt):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        fail("ERROR: OPENAI_API_KEY not set")

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-5.4-mini",
            "input": [
                {
                    "role": "system",
                    "content": "Return ONLY valid JSON. No explanation."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        },
        timeout=60
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
    except Exception:
        fail("Failed to parse JSON from model output")


def main():
    try:
        with open("specs/init.json", "r") as f:
            spec = json.load(f)
    except Exception as e:
        fail(f"Spec load error: {e}")

    prompt = f"""Generate files from this specification.

Return ONLY JSON in this format:

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

    result = call_openai(prompt)

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
