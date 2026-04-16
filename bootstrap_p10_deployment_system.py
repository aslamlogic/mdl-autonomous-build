import os
import subprocess
from textwrap import dedent


def write_file(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"UPDATED: {path}")


RUN_P10 = dedent("""
from dotenv import load_dotenv
load_dotenv()

import os
import subprocess
import requests


def create_github_repo(repo_name):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise Exception("GITHUB_TOKEN not set")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    r = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json={"name": repo_name, "private": True}
    )

    if r.status_code not in (200, 201):
        raise Exception(f"GitHub repo creation failed: {r.text}")

    return r.json()["html_url"]


def push_repo(repo_url):
    token = os.getenv("GITHUB_TOKEN")
    auth_url = repo_url.replace("https://", f"https://{token}@")

    subprocess.run(["git", "remote", "remove", "deploy-origin"], stderr=subprocess.DEVNULL)
    subprocess.run(["git", "remote", "add", "deploy-origin", auth_url], check=True)
    subprocess.run(["git", "push", "-u", "deploy-origin", "main"], check=True)


def create_render_service(repo_url):
    api_key = os.getenv("RENDER_API_KEY")
    owner = os.getenv("RENDER_OWNER_ID")

    if not api_key or not owner:
        raise Exception("Render environment variables missing")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "type": "web_service",
        "name": "mdl-autodeploy",
        "ownerId": owner,
        "repo": repo_url,
        "branch": "main",
        "runtime": "python",
        "buildCommand": "pip install -r requirements.txt",
        "startCommand": "uvicorn meta_ui.api:app --host 0.0.0.0 --port $PORT",
        "healthCheckPath": "/health"
    }

    r = requests.post(
        "https://api.render.com/v1/services",
        headers=headers,
        json=payload
    )

    if r.status_code not in (200, 201):
        raise Exception(f"Render service failed: {r.text}")

    return r.json()


def main():
    repo_name = "mdl-autonomous-build"

    print("Creating GitHub repo...")
    repo_url = create_github_repo(repo_name)

    print("Pushing code...")
    push_repo(repo_url)

    print("Creating Render service...")
    service = create_render_service(repo_url)

    print("DEPLOYMENT COMPLETE")
    print(service)


if __name__ == "__main__":
    main()
""")

write_file("run_p10_deploy.py", RUN_P10)

subprocess.run(["git", "add", "."], check=True)
subprocess.run(["git", "commit", "-m", "Add P10 deployment"], check=True)
subprocess.run(["git", "push"], check=True)

print("P10 FILES CREATED")
