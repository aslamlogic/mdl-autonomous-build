from flask import Flask, request, render_template_string, Response, jsonify
import time
import json

app = Flask(__name__)

# Mock database for the Action Research Ledger (v2.3.2)
research_ledger = []

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RUFLO NEXUS v2.3.2 - INTERACTIVE MONITOR</title>
    <style>
        body { background:#ffffff; color:#1f2328; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; padding:20px; display: flex; gap: 20px; font-size: 15px; }
        .main-panel { flex: 2; border:1px solid #d0d7de; padding:20px; border-radius:12px; background: #ffffff; }
        .research-panel { flex: 1.2; display: flex; flex-direction: column; gap: 15px; }
        .ledger-box { border:1px solid #d0d7de; padding:20px; border-radius:12px; background: #fffef0; flex-grow: 1; overflow-y: scroll; max-height: 400px; }
        .input-box { border:1px solid #d0d7de; padding:20px; border-radius:12px; background: #f6f8fa; }
        
        .layer-box { border:1px solid #d0d7de; margin:10px 0; padding:15px; border-left: 6px solid #d0d7de; border-radius: 6px; font-weight: bold; background: #f6f8fa; }
        .active { border-left-color: #0969da; background: #ddf4ff; }
        .completed { border-left-color: #1a7f37; background: #dafbe1; }
        
        .research-entry { font-size: 0.9em; border-bottom: 1px solid #d0d7de; padding: 10px 0; }
        .event-tag { color: #8250df; font-weight: bold; }
        
        #log-stream { background:#f6f8fa; color:#24292f; padding:15px; height:180px; overflow-y:scroll; border-radius:8px; font-family:monospace; border: 1px solid #d0d7de;}
        textarea { width: 95%; height: 60px; margin-top: 10px; border-radius: 6px; border: 1px solid #d0d7de; padding: 8px; font-family: sans-serif; }
        .btn-green { background:#1f883d; color:white; border:none; padding:10px 15px; border-radius:6px; cursor:pointer; font-weight: bold; }
        .btn-blue { background:#0969da; color:white; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="main-panel">
        <h1>Visual Nexus v2.3.2</h1>
        <div id="L1_SPEC" class="layer-box">L1 Spec Ingestion <span id="L1_SPEC_STATUS" style="float:right">WAITING</span></div>
        <div id="L1_GOV" class="layer-box">L1 Governance Audit <span id="L1_GOV_STATUS" style="float:right">WAITING</span></div>
        <div id="L1_GEN" class="layer-box">L1 Generation Layer <span id="L1_GEN_STATUS" style="float:right">WAITING</span></div>
        <div id="log-stream">Ready for Injection...</div>
        <form id="uploadForm" style="margin-top:15px;">
            <input type="file" name="file" required>
            <button type="submit" class="btn-green">INJECT CANONICAL SPEC</button>
        </form>
    </div>

    <div class="research-panel">
        <div class="input-box">
            <h3>Manual Research Input</h3>
            <textarea id="manualSuggestion" placeholder="Enter improvement or observation here..."></textarea>
            <button onclick="submitSuggestion()" class="btn-blue">Feed into Master Table</button>
        </div>
        <div class="ledger-box">
            <h3>Action Research Ledger</h3>
            <div id="research-feed"></div>
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
                if(data.research_event) { addEvent(data.research_event); }
                const log = document.getElementById('log-stream');
                log.innerHTML += '-> ' + data.msg + "\\n";
                log.scrollTop = log.scrollHeight;
                if(data.msg.includes("COMPLETE")) eventSource.close();
            };
        };

        function addEvent(msg) {
            const feed = document.getElementById('research-feed');
            const entry = document.createElement('div');
            entry.className = 'research-entry';
            entry.innerHTML = `<span class="event-tag">[EVENT]</span> ${msg}`;
            feed.prepend(entry);
        }

        async function submitSuggestion() {
            const text = document.getElementById('manualSuggestion').value;
            if(!text) return;
            addEvent("MANUAL: " + text);
            document.getElementById('manualSuggestion').value = '';
            // Backend storage simulation
            console.log("Suggestion logged to Master Table:", text);
        }
    </script>
</body>
</html>
'''

@app.route('/inject_spec', methods=['POST'])
def inject():
    global build_events
    build_events = [
        {"layer": "L1_SPEC", "state": "active", "msg": "Analyzing .txt substrate...", "research_event": "AR-INF-002: Substrate Parity Verified."},
        {"layer": "L1_SPEC", "state": "completed", "msg": "Spec Ingested.", "research_event": "AR-UI-005: Manual Input Port v2.3.2 Active."},
        {"layer": "L1_GOV", "state": "active", "msg": "Auditing Supra-MetaRules v5.6...", "research_event": "AR-GOV-001: Truth Discipline Active."},
        {"layer": "L1_GEN", "state": "active", "msg": "Generating DDL...", "research_event": "AR-GEN-001: SQL Schema Mapping Initiated."},
        {"layer": "L1_GEN", "state": "completed", "msg": "BUILD COMPLETE.", "research_event": "EVENT: v2.3.2 Integration Succeeded."}
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
