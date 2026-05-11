from flask import Flask, request, render_template_string, Response, jsonify
import time
import json

app = Flask(__name__)

# Mock database for the Action Research Ledger
research_ledger = []

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RUFLO NEXUS v2.3 - RESEARCH & BUILD MONITOR</title>
    <style>
        body { background:#0d1117; color:#c9d1d9; font-family:monospace; padding:20px; display: flex; gap: 20px; }
        .main-panel { flex: 2; border:1px solid #30363d; padding:20px; border-radius:8px; background: #0d1117; }
        .research-panel { flex: 1; border:1px solid #30363d; padding:20px; border-radius:8px; background: #161b22; }
        .layer-box { border:1px solid #30363d; margin:10px 0; padding:15px; border-left: 5px solid #30363d; }
        .active { border-left-color: #58a6ff; background: #1c2128; }
        .completed { border-left-color: #238636; }
        .research-entry { font-size: 0.85em; border-bottom: 1px solid #30363d; padding: 10px 0; color: #8b949e; }
        .event-tag { color: #d2a8ff; font-weight: bold; }
        #log-stream { background:#000; color:#7ee787; padding:10px; height:150px; overflow-y:scroll; border-radius:4px; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="main-panel">
        <h1>Visual Nexus Build (v2.2 -> v2.3)</h1>
        <div id="L1_SPEC" class="layer-box">L1 Spec Layer <span id="L1_SPEC_STATUS" style="float:right">WAITING</span></div>
        <div id="L1_GOV" class="layer-box">L1 Governance Layer <span id="L1_GOV_STATUS" style="float:right">WAITING</span></div>
        <div id="L1_GEN" class="layer-box">L1 Generation Layer <span id="L1_GEN_STATUS" style="float:right">WAITING</span></div>
        <div id="log-stream">Ready for Injection...</div>
        <br>
        <form id="uploadForm">
            <input type="file" name="file" required>
            <button type="submit" style="background:#238636; color:white; border:none; padding:10px; border-radius:4px; cursor:pointer;">INJECT SPEC</button>
        </form>
    </div>

    <div class="research-panel">
        <h3>Action Research Master Table</h3>
        <div id="research-feed">
            <p style="color:#484f58 italic">Awaiting events...</p>
        </div>
    </div>

    <script>
        const form = document.getElementById('uploadForm');
        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            fetch('/inject_spec', { method: 'POST', body: formData });

            const eventSource = new EventSource('/progress');
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if(data.layer) {
                    document.getElementById(data.layer).className = 'layer-box ' + data.state;
                    document.getElementById(data.layer + '_STATUS').innerText = data.state.toUpperCase();
                }
                if(data.research_event) {
                    const feed = document.getElementById('research-feed');
                    const entry = document.createElement('div');
                    entry.className = 'research-entry';
                    entry.innerHTML = `<span class="event-tag">[EVENT]</span> ${data.research_event}`;
                    feed.prepend(entry);
                }
                const log = document.getElementById('log-stream');
                log.innerHTML += data.msg + "\\n";
                log.scrollTop = log.scrollHeight;
                if(data.msg.includes("COMPLETE")) eventSource.close();
            };
        };
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/inject_spec', methods=['POST'])
def inject():
    global build_events
    build_events = [
        {"layer": "L1_SPEC", "state": "active", "msg": "Analyzing .txt substrate...", "research_event": "AR-INF-002: Substrate Parity Verified."},
        {"layer": "L1_SPEC", "state": "completed", "msg": "Spec Ingested.", "research_event": "AR-UI-001: Telemetry HUD Requirement Logged for v2.3."},
        {"layer": "L1_GOV", "state": "active", "msg": "Auditing Supra-MetaRules...", "research_event": "AR-GOV-001: Truth Discipline Active."},
        {"layer": "L1_GEN", "state": "active", "msg": "Generating DDL...", "research_event": "AR-GEN-001: SQL Schema Mapping Initiated."},
        {"layer": "L1_GEN", "state": "completed", "msg": "BUILD COMPLETE.", "research_event": "EVENT: v2.3 Specification Updated via Action Research."}
    ]
    return "Started", 200

@app.route('/progress')
def progress():
    def generate():
        for event in build_events:
            yield f"data: {json.dumps(event)}\\n\\n"
            time.sleep(2)
    return Response(generate(), mimetype='text/event-stream')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
