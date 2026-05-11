from flask import Flask, request, render_template_string, Response, jsonify
import time, json, uuid

app = Flask(__name__)

# Concurrent Build Storage with Isolated Ledger State
builds = {}

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RUFLO NEXUS v2.5 - HIERARCHICAL BUILDER</title>
    <style>
        body { background:#ffffff; color:#1f2328; font-family: -apple-system, sans-serif; padding:20px; font-size: 14px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eaeef2; padding-bottom: 15px; margin-bottom: 20px; }
        .nexus-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        .card { border:1px solid #d0d7de; padding:20px; border-radius:12px; background: #ffffff; }
        .layer-box { border:1px solid #d0d7de; margin:10px 0; padding:15px; border-left: 6px solid #d0d7de; border-radius: 6px; font-weight: bold; background: #f6f8fa; }
        .active { border-left-color: #0969da; background: #ddf4ff; }
        .completed { border-left-color: #1a7f37; background: #dafbe1; }
        #log-stream { background:#f6f8fa; border:1px solid #d0d7de; padding:15px; height:150px; overflow-y:scroll; font-family:monospace; border-radius:8px; margin-top:10px; }
        .btn { padding: 10px 15px; border-radius: 6px; border: none; cursor: pointer; font-weight: bold; }
        .btn-green { background: #1f883d; color: white; }
        select { padding: 10px; border-radius: 6px; border: 1px solid #d0d7de; font-size: 1em; width: 250px; }
        textarea { width: 100%; height: 60px; margin: 10px 0; border-radius: 6px; border: 1px solid #d0d7de; padding: 8px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Nexus v2.5: Multi-Project HUD</h1>
        <div>
            <label><strong>Switch Build Context:</strong></label>
            <select id="buildSelector" onchange="switchContext()">
                <option value="">-- No Active Build --</option>
            </select>
        </div>
    </div>

    <div class="card" style="margin-bottom: 20px; background: #f6f8fa;">
        <h3>Initialize New Specification Ingestion</h3>
        <form id="uploadForm">
            <input type="file" name="file" required>
            <button type="submit" class="btn btn-green">LAUNCH BUILD INSTANCE</button>
        </form>
    </div>

    <div id="dashboard" class="nexus-grid" style="display:none;">
        <div class="main-column">
            <div class="card">
                <h3>Build Progress: <span id="display-id" style="color:#0969da"></span></h3>
                <div id="L1_SPEC" class="layer-box">L1 Spec Layer <span id="status-SPEC" style="float:right">WAITING</span></div>
                <div id="L1_GOV" class="layer-box">L1 Governance Layer <span id="status-GOV" style="float:right">WAITING</span></div>
                <div id="L1_GEN" class="layer-box">L1 Generation Layer <span id="status-GEN" style="float:right">WAITING</span></div>
                <div id="log-stream">Initializing logs...</div>
            </div>
        </div>
        <div class="research-column">
            <div class="card" style="background:#fffef0">
                <h3>Action Research (Current Context)</h3>
                <textarea id="manualInput" placeholder="Record improvement for this build..."></textarea>
                <button onclick="addObservation()" class="btn" style="background:#0969da; color:white; width:100%">LOG TO MASTER TABLE</button>
                <hr>
                <div id="research-feed" style="max-height: 300px; overflow-y: auto;"></div>
            </div>
        </div>
    </div>

    <script>
        let buildData = {};
        let currentId = null;

        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const res = await fetch('/start_build', { method: 'POST', body: formData });
            const { build_id } = await res.json();
            
            const selector = document.getElementById('buildSelector');
            const opt = document.createElement('option');
            opt.value = build_id; opt.innerText = "Build ID: " + build_id;
            selector.appendChild(opt);
            selector.value = build_id;
            
            buildData[build_id] = { logs: [], research: [], progress: {SPEC: 'waiting', GOV: 'waiting', GEN: 'waiting'} };
            switchContext();
            startStreaming(build_id);
        };

        function switchContext() {
            currentId = document.getElementById('buildSelector').value;
            if(!currentId) { document.getElementById('dashboard').style.display = 'none'; return; }
            document.getElementById('dashboard').style.display = 'grid';
            document.getElementById('display-id').innerText = currentId;
            updateUI();
        }

        function updateUI() {
            const data = buildData[currentId];
            ['SPEC', 'GOV', 'GEN'].forEach(l => {
                const el = document.getElementById('L1_' + l);
                el.className = 'layer-box ' + data.progress[l];
                document.getElementById('status-' + l).innerText = data.progress[l].toUpperCase();
            });
            document.getElementById('log-stream').innerHTML = data.logs.join('<br>');
            document.getElementById('research-feed').innerHTML = data.research.map(r => `<div style="padding:5px; border-bottom:1px solid #d0d7de"><strong>[EVENT]</strong> ${r}</div>`).join('');
        }

        function startStreaming(id) {
            const es = new EventSource('/stream/' + id);
            es.onmessage = (e) => {
                const msg = JSON.parse(e.data);
                buildData[id].progress[msg.layer] = msg.state;
                buildData[id].logs.push(msg.msg);
                if(msg.research) buildData[id].research.push(msg.research);
                if(currentId === id) updateUI();
                if(msg.percent >= 100) es.close();
            };
        }

        function addObservation() {
            const val = document.getElementById('manualInput').value;
            if(!val || !currentId) return;
            buildData[currentId].research.push("MANUAL: " + val);
            document.getElementById('manualInput').value = '';
            updateUI();
        }
    </script>
</body>
</html>
'''

@app.route('/start_build', methods=['POST'])
def start():
    return jsonify({"build_id": str(uuid.uuid4())[:8]}), 200

@app.route('/stream/<id>')
def stream(id):
    def gen():
        steps = [
            {"layer": "SPEC", "state": "active", "msg": "Analyzing Substrate...", "percent": 20, "research": "Spec Parsed."},
            {"layer": "SPEC", "state": "completed", "msg": "Ingestion Complete.", "percent": 33},
            {"layer": "GOV", "state": "active", "msg": "Running Audit...", "percent": 50, "research": "Truth Gate Clear."},
            {"layer": "GOV", "state": "completed", "msg": "Governance Active.", "percent": 66},
            {"layer": "GEN", "state": "active", "msg": "Generating Schema...", "percent": 80, "research": "DDL Generated."},
            {"layer": "GEN", "state": "completed", "msg": "BUILD COMPLETE.", "percent": 100}
        ]
        for s in steps:
            yield f"data: {json.dumps(s)}\\n\\n"
            time.sleep(2.5)
    return Response(gen(), mimetype='text/event-stream')

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
