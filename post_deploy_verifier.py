#!/usr/bin/env python3
import os, sys, subprocess, time, json
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: requests library missing. Run: pip install requests")
    sys.exit(2)

TARGET_URL = os.environ.get('TARGET_URL', 'https://mdl-autonomous-build.onrender.com')
BRANCH = os.environ.get('BRANCH', 'main')
GIT_REMOTE = os.environ.get('GIT_REMOTE', 'origin')
RETRY_INTERVAL = 10
TOTAL_TIMEOUT = 600

def check_endpoints(url):
    results = {}
    try:
        results['root'] = requests.get(url + '/', timeout=5).status_code
        results['health'] = requests.get(url + '/health', timeout=5).status_code
        # Minimal probe to verify /run exists
        results['run'] = requests.post(url + '/run', json={"instruction":"test"}, timeout=5).status_code
    except Exception as e:
        results['error'] = str(e)
    return results

def git_fix():
    print("Contract Violation Detected. Injecting P11 self-correction...")
    main_py = "import os\nfrom meta_ui.api import app\nif __name__ == '__main__':\n    import uvicorn\n    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))"
    with open('main.py', 'w') as f: f.write(main_py)
    subprocess.run(['git', 'add', 'main.py'])
    subprocess.run(['git', 'commit', '-m', 'chore: post-deploy contract fix [SMR v5.6]'])
    subprocess.run(['git', 'push', GIT_REMOTE, BRANCH])

print(f"Starting Contract Verification: {TARGET_URL}")
initial = check_endpoints(TARGET_URL)
print(f"Initial State: {initial}")

if initial.get('root') != 200 or initial.get('health') != 200:
    git_fix()
    print("Fix pushed. Polling for recovery (this takes minutes based on Render build time)...")
    start = time.time()
    while time.time() - start < TOTAL_TIMEOUT:
        time.sleep(RETRY_INTERVAL)
        current = check_endpoints(TARGET_URL)
        if current.get('root') == 200 and current.get('health') == 200:
            print("\nRecovery Verified. Status: Live")
            sys.exit(0)
        print(".", end="", flush=True)
    print("\nTimeout: Manual Intervention Required.")
    sys.exit(3)
else:
    print("Contract Valid. Factory Operational.")
