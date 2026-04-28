#!/usr/bin/env bash
set -euo pipefail

# 1. Force the UI code into api.py (since Render is stuck running this file)
cat > meta_ui/api.py <<'PY'
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import os

app = FastAPI(title="MDL Autonomous Build Factory")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MDL Factory Control</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans">
    <nav class="border-b border-slate-800 p-4 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto flex justify-between items-center">
            <h1 class="text-xl font-bold tracking-tight text-blue-400">MDL <span class="text-slate-400">FACTORY</span></h1>
            <div class="flex gap-4">
                <span id="status-badge" class="px-3 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/20">System Live</span>
            </div>
        </div>
    </nav>
    <main class="max-w-7xl mx-auto p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="md:col-span-1 space-y-6">
            <div class="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
                <h2 class="text-lg font-semibold mb-4 flex items-center gap-2 font-mono">
                    <i data-lucide="play" class="w-5 h-5 text-blue-400"></i> TRIGGER_BUILD
                </h2>
                <div class="space-y-4">
                    <input id="build-cmd" type="text" placeholder="Build Instruction..." class="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none font-mono">
                    <button onclick="runBuild()" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-lg transition-all font-mono uppercase tracking-widest">Execute</button>
                </div>
            </div>
        </div>
        <div class="md:col-span-2 space-y-6">
            <div class="bg-slate-800/50 rounded-xl border border-slate-700 p-6 overflow-hidden">
                <h2 class="text-lg font-semibold mb-4 flex items-center gap-2 font-mono">
                    <i data-lucide="terminal" class="w-5 h-5 text-emerald-400"></i> CAPTURE_SINK_STREAM
                </h2>
                <div id="log-container" class="bg-slate-900 rounded-lg p-4 h-[400px] font-mono text-xs overflow-y-auto space-y-2 border border-slate-800">
                    <div class="text-slate-500 italic">Connected to Factory Worker...</div>
                </div>
            </div>
        </div>
    </main>
    <script>
        lucide.createIcons();
        async function runBuild() {
            const cmd = document.getElementById('build-cmd').value;
            const container = document.getElementById('log-container');
            container.innerHTML += `<div class="text-blue-400">[CMD] ${cmd}</div>`;
            try {
                const res = await fetch('/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: cmd})
                });
                const data = await res.json();
                container.innerHTML += `<div class="text-green-400">[ACK] ${JSON.stringify(data)}</div>`;
            } catch (err) {
                container.innerHTML += `<div class="text-red-400">[ERR] ${err}</div>`;
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTML_TEMPLATE

@app.get("/health")
async def health():
    return {"status": "ok", "mode": "provisioned_api_sync"}

@app.post("/run")
async def run(request: Request):
    data = await request.json()
    return {"status": "accepted", "instruction": data.get("command")}
PY

# 2. Sync main.py just in case
cp meta_ui/api.py meta_ui/main.py

# 3. Commit and Push
git add meta_ui/api.py meta_ui/main.py
git commit -m "fix: force UI onto api.py entrypoint for Render compatibility"
git push origin main

echo "SYNC COMPLETE. Refresh the root URL in 2 minutes."
