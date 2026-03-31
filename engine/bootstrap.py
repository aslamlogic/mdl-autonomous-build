import os
import json
import requests
import re

API_URL = "https://api.anthropic.com/v1/messages"

def extract_json(text):
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except:
        pass

    # Extract largest JSON block (handles extra text / markdown)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception as e:
            print("Regex JSON parse failed:", e)

    print("Failed to extract valid JSON")
    return {"files": []}


def call_claude(prompt):
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("ERROR: CLAUDE_API_KEY not set")
        return {"files": []}

    response = requests.post(
        API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    if response.status_code != 200:
        print(f"Claude API error: {response.text}")
        return {"files": []}

    data = response.json()
    text = data["content"][0]["text"]

    print("===== CLAUDE RAW OUTPUT =====")
    print(text)
    print("===== END OUTPUT =====")

    return extract_json(text)


def main():
    with open("specs/init.json", "r") as f:
        spec = json.load(f)

    prompt = f"""You are an expert software engineer.

IMPORTANT:
- Do NOT include markdown
- Do NOT include explanations
- Output must be pure JSON only
- The response must start with {{ and end with }}

Return ONLY valid JSON in this structure:

{{
  "files": [
    {{
      "path": "path/to/file1.py",
      "content": "full file content here"
    }}
  ]
}}

Specification:
{spec}
"""

    result = call_claude(prompt)

    for file_entry in result.get("files", []):
        path = file_entry.get("path")
        content = file_entry.get("content", "")

        if path and content:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"✓ Wrote: {path}")


if __name__ == "__main__":
    main()