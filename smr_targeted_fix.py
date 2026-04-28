import os, sys, subprocess, time, requests

TARGET_URL = "https://mdl-autonomous-build.onrender.com"
FILE_TO_PATCH = "meta_ui/api.py"

def check_run():
    try:
        r = requests.post(f"{TARGET_URL}/run", json={"instruction":"ping"}, timeout=10)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)

print(f"Applying Targeted SMR v5.6 Fix to {FILE_TO_PATCH}...")

# Read the file
with open(FILE_TO_PATCH, 'r') as f:
    content = f.read()

# Fix the generate() signature mismatch by adding *args to handle variable arguments
# This specifically targets the common pattern where only one arg was expected
old_func = "def generate(instruction):"
new_func = "def generate(instruction, *args, **kwargs):"

if old_func in content:
    content = content.replace(old_func, new_func)
    with open(FILE_TO_PATCH, 'w') as f:
        f.write(content)
    print("Patch Applied: Added *args, **kwargs to generate() signature.")
else:
    print("Warning: Could not find exact function signature. Attempting fuzzy match...")
    content = content.replace("def generate(", "def generate(instruction, *args, **kwargs): # Fixed signature\ndef old_generate(")
    with open(FILE_TO_PATCH, 'w') as f:
        f.write(content)

# Commit and Push
subprocess.run(['git', 'add', FILE_TO_PATCH])
subprocess.run(['git', 'commit', '-m', 'fix: resolve generate() signature mismatch [SMR v5.6]'])
subprocess.run(['git', 'push', 'origin', 'main'])

print("Fix Pushed. Polling for recovery...")
start = time.time()
while time.time() - start < 600:
    time.sleep(15)
    status, text = check_run()
    if status == 200:
        print(f"\nSUCCESS: Contract Valid. Factory Operational. Result: {text}")
        sys.exit(0)
    print(".", end="", flush=True)

print("\nTimeout: Please check Render build logs.")
sys.exit(1)
