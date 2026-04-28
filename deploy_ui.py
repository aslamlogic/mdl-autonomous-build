#!/usr/bin/env python3
"""
deploy_ui.py  —  SMR v5.6 UI Deployer
Upload this file to your Codespace root, then run:
    python deploy_ui.py
It will write all files and push to GitHub automatically.
"""
import base64, gzip, subprocess, sys
from pathlib import Path

HTML_GZ  = "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"
API_GZ   = "H4sIAEcQ8WkC/51UTU/jMBC951dYPiUoBA67l0qRtgtdqbuUosJlhVBk4mlr4djGdqDViv/OOF9NgdP2Envmvfl4M+7a6oqsmfPMCCIqo60nv/A6vZlH65Evs+CMVg7cgBISVp0xJb9vl9f97ZhYCc4lvDILWantQL9Yrm4Xg6ulmD1nyouyx/xkDhaag+zczG+leOy9N3htHX5vhNr09qXxQismo+6uXUrc3kUtVniwLACwGuWtlhJszzxYoogZQ/JeitgLLyGni8srMq29VrrStUNv6bXd06SBZ4zz4tBtHBH8HbeZNjYmpX4ttBUboVx+T0/ow9hRWuCAMjDp8jtbH5Eq8FvNvyBtgXGwgwMrur2b3s0visv5CvsIWsVFscaZFUWSGaxF+e5DzgjFUaHuNIpKyZwjq1qt4LkG5+NhBsmkSYcle1uXQcEJwWNjdAbKySD8PRelf8Cs11pBFP0I2mzAx/QMleKwJrUorNY+7kPyHYJH9WJBQnHYZVtfSdpi1gGWwU4473pi+FnwtVVH2xhjWTGikyQaIf41TdaOTgjVTzQltBbhXAnnwva0EpyNEr8d1Y4KS7/tOmgvfR1fZzimc8E2HTkcP1KHfqjZ44gVxsCdzV5wpqhpenBrA4qJAl9W8QT7woFH6KPWMtYupAL1EtPlzex6Oi9wc4s/s780ST4HqMJMkfqZtVhezq6CPhvjT7/p00ooQbsIfU9Gu9CUrVXXE55iC8+T0ep0HXq7H0/L1dLjtA9PLeuo2WizkoEQ5u6Ch6kS4paekrBgCWGKdwFbjTv1E5LnhIK12tJD5pHY4/+quCUVJcqRfz8/T5vK8FXk42m2wVJyctLme0s+7t8Y7eqyBOeChC0cjR2vocGuBOPJrPlgt4Q5Ap82+v+rpBVmZxugzQONIcFy3wHZyAsS6AUAAA=="

def decode(s):
    return gzip.decompress(base64.b64decode(s))

def run(cmd, **kw):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, **kw)
    if r.returncode != 0:
        print(f"ERROR: command failed (exit {r.returncode})")
        sys.exit(r.returncode)

root = Path.cwd()
print(f"[deploy_ui] Working in {root}")

# 1. Write UI
(root / "static").mkdir(exist_ok=True)
(root / "static" / "index.html").write_bytes(decode(HTML_GZ))
print("[deploy_ui] Written: static/index.html")

# 2. Patch API
(root / "meta_ui").mkdir(exist_ok=True)
(root / "meta_ui" / "api.py").write_bytes(decode(API_GZ))
print("[deploy_ui] Written: meta_ui/api.py")

# 3. Ensure aiofiles in requirements
req = root / "requirements.txt"
if req.exists():
    txt = req.read_text(encoding="utf-8")
    if "aiofiles" not in txt:
        req.write_text(txt.rstrip() + "\naiofiles\n", encoding="utf-8")
        print("[deploy_ui] Updated: requirements.txt (added aiofiles)")

# 4. Git commit and push
run("git add .")
run('git commit -m "SMR v5.6: Production UI deployed"')
run("git push")

print("\n[deploy_ui] DONE. Render will redeploy automatically.")
print("[deploy_ui] Live at: https://mdl-autonomous-build.onrender.com/")
