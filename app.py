from flask import Flask, render_template_string, jsonify, request
import datetime

app = Flask(__name__)

# Forensic Context
KNOWN_REPOS = ["evidentia-app"]
SPEC_FILE = "Evidentia specification v2.2.txt"

@app.route('/')
def home():
    return render_template_string(HUD_HTML)

@app.route('/api/execute_mode', methods=['POST'])
def execute_mode():
    data = request.json
    mode = data.get('mode')
    repo = data.get('repo', 'New-Build-Context')
    
    logs = []
    if mode == "repair":
        logs = [
            f"Tethering to existing repo: {repo}",
            f"Ingesting {SPEC_FILE} for gap analysis...",
            "Forensic Audit: Identifying missing § clauses in /src...",
            "Ruflo Swarm: Plugging gaps in Legal Reasoning Engine."
        ]
    else:
        logs = [
            "Initializing Fresh Substrate...",
            f"Mapping {SPEC_FILE} to new database schema...",
            "Generating core TypeScript boilerplate...",
            "Deploying fresh build to Render lab."
        ]
        
    return jsonify({
        "timestamp": datetime.datetime.now().strftime('%H:%M:%S'),
        "mode": mode,
        "logs": logs
    })

HUD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>RUFLO BRAIN v3.5 - BIMODAL HUD</title>
    <style>
        body { background:#ffffff; color:#1f2328; font-family: -apple-system, sans-serif; padding:40px; }
        .nexus-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }
        .card { border:1px solid #d0d7de; padding:35px; border-radius:12px; background: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .mode-btn { padding: 20px; font-size: 18px; font-weight: bold; border-radius: 10px; border: none; cursor: pointer; transition: 0.2s; width: 100%; margin-top: 15px; }
        .btn-anew { background: #1f883d; color: white; }
        .btn-repair { background: #0969da; color: white; }
        #console { background:#0d1117; color:#7ee787; padding:20px; height:350px; overflow-y:scroll; border-radius:8px; font-family:monospace; margin-top: 20px; font-size: 14px; }
        .spec-tag { background: #f6f8fa; padding: 10px; border: 1px solid #d0d7de; border-radius: 6px; font-weight: bold; display: block; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div style="border-bottom: 2px solid #eaeef2; margin-bottom: 30px; padding-bottom: 20px;">
        <h1>aslamlogic // Ruflo Central Brain v3.5</h1>
        <span class="spec-tag">Source: Evidentia specification v2.2.txt</span>
    </div>

    <div class="nexus-grid">
        <div class="card">
            <h2>Select Operation Mode</h2>
            
            <div style="margin-bottom: 30px;">
                <p><strong>Path A:</strong> Initialize a brand new repository from the specification text.</p>
                <button onclick="run('anew')" class="mode-btn btn-anew">BUILD ANEW</button>
            </div>
            <hr>
            <div style="margin-top: 30px;">
                <p><strong>Path B:</strong> Audit and plug gaps in a previously existing repository.</p>
                <select id="repoSelect" style="width:100%; padding:15px; border-radius:8px; margin-bottom:15px;">
                    <option value="evidentia-app">Target: aslamlogic/evidentia-app</option>
                </select>
                <button onclick="run('repair')" class="mode-btn btn-repair">REPAIR / UPDATE REPO</button>
            </div>
        </div>

        <div class="card">
            <h2>Swarm Telemetry</h2>
            <div id="console">Awaiting mode selection...</div>
        </div>
    </div>

    <script>
        async function run(mode) {
            const consoleBox = document.getElementById('console');
            const repo = document.getElementById('repoSelect').value;
            consoleBox.innerHTML = `[SYSTEM] Mode: ${mode.toUpperCase()} initiated...<br>`;
            
            const res = await fetch('/api/execute_mode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ mode, repo })
            });
            const data = await res.json();
            
            data.logs.forEach((log, i) => {
                setTimeout(() => {
                    consoleBox.innerHTML += `[${data.timestamp}] ${log}<br>`;
                    consoleBox.scrollTop = consoleBox.scrollHeight;
                }, i * 1500);
            });
        }
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
