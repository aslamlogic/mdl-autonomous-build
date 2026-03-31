import os
import json
import requests

API_URL = "https://api.anthropic.com/v1/messages"

def call_claude(prompt):
    r = requests.post(
        API_URL,
        headers={
            "x-api-key": os.getenv("CLAUDE_API_KEY"),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-3-5-sonnet-20240620",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    try:
        data = r.json()
        if "content" in data:
            return json.loads(data["content"][0]["text"])
    except:
        pass

    return {"files": []}


def main():
    with open("specs/init.json") as f:
        spec = json.load(f)

    result = call_claude(str(spec))

    for f in result.get("files", []):
        os.makedirs(os.path.dirname(f["path"]), exist_ok=True)
        with open(f["path"], "w") as file:
            file.write(f["content"])


if __name__ == "__main__":
    main()
