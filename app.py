from flask import Flask, request, render_template_string, Response, jsonify
import time
import json

app = Flask(__name__)

# Mock database for the Action Research Ledger (v2.3.1)
research_ledger = []

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RUFLO NEXUS v2.3.1 - ACCESSIBLE MONITOR</title>
    <style>
        body { background:#ffffff; color:#1f2328; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; padding:30px; display: flex; gap: 30px; font-size: 16px; }
        .main-panel { flex: 2; border:1px solid #d0d7de; padding:25px; border-radius:12px; background: #ffffff; }
        .research-panel { flex: 1; border:1px solid #d0d7de; padding:25px; border-radius:12px; background: #fffef0; }
        h1, h3 { color: #1f2328; font-family: monospace; border-bottom: 2px solid #eaeef2; padding-bottom: 10px; }
        
        /* Layer HUD Styles */
        .layer-box { border:1px solid #d0d7de; margin:15px 0; padding:20px; border-left: 8px solid #d0d7de; border-radius: 6px; font-weight: bold; background: #f6f8fa; color: #57606a;}
        .active { border-left-color: #0969da; background: #ddf4ff; color: #0969da; }
        .completed { border-left-color: #1a7f37; background: #dafbe1; color: #1a7f37; }
        
        /* Research Event Styles */
        .research-entry { font-size: 0.95em; border-bottom: 1px solid #d0d7de; padding: 15px 0; color: #24292f; }
        .event-tag { color: #8250df; font-weight: bold; font-family: monospace; }
        
        /* Large Font Log */
        #log-stream { background:#f6f8fa; color:#24292f; padding:20px; height:250px; overflow-y:scroll; border-radius:8px; font-family:monospace; font-size: 1.1em; line-height: 1.6; border: 1px solid #d0d7de;}
        
        form { margin-top: 20px; padding: 15px; background: #f6f8fa; border-radius: 8px; border: 1px solid #d0d7de;}
        button { background:#1f883d; color:white; border:none; padding:12px 20px; border-radius:8px; cursor:pointer; font-weight: bold; font-size: 1em; }
        input[type="file"] { font-size: 1em; padding: 8px; }
    </style>
</head>
<body>
    <div class="main-panel">
        <h1>Visual Nexus Build (v2.2 -> v2.3.1)</h1>
        <div id="L1_SPEC" class="layer-box">L1 Spec Ingestion Layer <span id="L1_SPEC_STATUS" style="float:right">WAITING</span></div>
        <div id="L1_GOV" class="layer-box">L1 Governance Audit Layer <span id="L1_GOV_STATUS" style="float:right">WAITING</span></div>
        <div id="L1_GEN" class="layer-box">L1 Generation Layer (SQL) <span id="L1_GEN_STATUS" style="float:right">WAITING</span></div>
        <div id="log-stream">Ready for Canonical Specification Ingestion...</div>
        <br>
        <form id="uploadForm">
            <input type="file" name="file" required>
            <button type="submit">INJECT CANONICAL SPEC</button>
        </form>
    </div>

    <div class="research-panel">
        <h3>Action Research Master Table</h3>
        <div id="research-feed">
            <p style="color:#57606a italic">Awaiting Research Events...</p>
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
                    if (feed.firstChild && feed.firstChild.style && feed.firstChild.style.fontStyle === 'italic') { feed.innerHTML = ''; }
                    const entry = document.createElement('div');
                    entry.className = 'research-entry';
                    entry.innerHTML = `<span class="event-tag">[EVENT]</span> ${data.research_event}`;
                    feed.prepend(entry);
                }
                const log = document.getElementById('log-stream');
                log.innerHTML += '-> ' + data.msg + "\\n";
                log.scrollTop = log.scrollHeight;
                if(data.msg.includes("COMPLETE")) eventSource.close();
            };
        };
    </script>
</body>
</html>
'''

@app.route('/inject_spec', methods=['POST'])
def inject():
    global build_events
    build_events = [
        {"layer": "L1_SPEC", "state": "active", "msg": "Analyzing .txt substrate...", "research_event": "AR-INF-002: Substrate Parity Verified."},
        {"layer": "L1_SPEC", "state": "completed", "msg": "Spec Ingested.", "research_event": "AR-UI-004: Accessible UI Update Logged (Refactor v2.3.1)."},
        {"layer": "L1_GOV", "state": "active", "msg": "Auditing Supra-MetaRules v5.6...", "research_event": "AR-GOV-001: Truth Discipline Active."},
        {"layer": "L1_GEN", "state": "active", "msg": "Generating DDL...", "research_event": "AR-GEN-001: SQL Schema Mapping Initiated."},
        {"layer": "L1_GEN", "state": "completed", "msg": "BUILD COMPLETE.", "research_event": "EVENT: v2.3.1 Target Achieved (Telemetry & Accessibility)."}
    ]
    return "Started", 200

@app.route('/progress')
def progress():
    def generate():
        for event in build_events:
            yield f"data: {json.dumps(event)}\\n\\n"
            time.sleep(2.5)
    return Response(generate(), mimetype='text/event-stream')

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
