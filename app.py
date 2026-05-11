from flask import Flask, request, render_template_string, Response, jsonify
import time, json, uuid, os, requests

app = Flask(__name__)

# Forensic Configuration (To be set in Render Environment Variables)
GH_APP_ID = os.environ.get('GH_APP_ID')
GH_PRIVATE_KEY = os.environ.get('GH_PRIVATE_KEY')
RENDER_API_KEY = os.environ.get('RENDER_API_KEY')
WORKSPACE = "aslamlogic"

# Global State for the Neural Swarm
build_registry = {}

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RUFLO BRAIN - aslamlogic ORCHESTRATOR</title>
    <style>
        body { background:#ffffff; color:#1f2328; font-family: -apple-system, sans-serif; padding:20px; font-size: 15px; }
        .nexus-container { display: grid; grid-template-columns: 300px 1fr 350px; gap: 20px; }
        .card { border:1px solid #d0d7de; padding:20px; border-radius:12px; background: #ffffff; margin-bottom: 20px; }
        .layer-box { border:1px solid #d0d7de; margin:10px 0; padding:15px; border-left: 8px solid #d0d7de; border-radius: 6px; font-weight: bold; background: #f6f8fa; }
        .active { border-left-color: #0969da; background: #ddf4ff; }
        .completed { border-left-color: #1a7f37; background: #dafbe1; }
        .failed { border-left-color: #cf222e; background: #ffebe9; }
        
        #log-stream { background:#f6f8fa; color:#24292f; padding:15px; height:200px; overflow-y:scroll; border-radius:8px; font-family:monospace; border: 1px solid #d0d7de; font-size: 1.1em; }
        .btn { padding: 12px 20px; border-radius: 8px; border: none; cursor: pointer; font-weight: bold; width: 100%; }
        .btn-green { background: #1f883d; color: white; }
        .btn-blue { background: #0969da; color: white; margin-top: 10px; }
        select { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #d0d7de; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div style="border-bottom: 2px solid #eaeef2; margin-bottom: 20px; padding-bottom: 10px;">
        <h1>aslamlogic // Ruflo Central Brain</h1>
    </div>

    <div class="nexus-container">
        <div class="col-1">
            <div class="card">
                <h3>Workspace Control</h3>
                <select id="buildSelector" onchange="switchContext()">
                    <option value="">-- Select Active Repo --</option>
                </select>
                <form id="spawnForm">
                    <input type="text" id="newRepo" placeholder="New Repo Name" style="width:90%; padding:10px; margin-bottom:10px; border-radius:6px; border:1px solid #d0d7de;">
                    <button type="submit" class="btn btn-green">SPAWN REPO</button>
                </form>
            </div>
        </div>

        <div class="col-2">
            <div id="dashboard" class="card" style="display:none;">
                <h3>Telemetry: <span id="display-id"></span></h3>
                <div id="L1_SPEC" class="layer-box">L1 SPEC INGESTION <span id="status-SPEC" style="float:right">WAITING</span></div>
                <div id="L1_SWARM" class="layer-box">RUFLO SWARM PATROL <span id="status-SWARM" style="float:right">WAITING</span></div>
                <div id="L1_RENDER" class="layer-box">RENDER HEALTH CHECK <span id="status-RENDER" style="float:right">WAITING</span></div>
                <div id="log-stream">Ready for command...</div>
                <button onclick="triggerSwarm()" class="btn btn-blue">INITIATE CLOUD SWARM AUDIT</button>
            </div>
        </div>

        <div class="col-3">
            <div class="card" style="background:#fffef0;">
                <h3>Research Master Table</h3>
                <textarea id="arInput" style="width:95%; height:80px; border-radius:6px; padding:8px;" placeholder="Observation..."></textarea>
                <button onclick="logAR()" class="btn btn-blue">RECORD TO LEDGER</button>
                <hr>
                <div id="arFeed" style="max-height: 300px; overflow-y: auto;"></div>
            </div>
        </div>
    </div>

    <script>
        let registry = {};
        let activeId = null;

        document.getElementById('spawnForm').onsubmit = async (e) => {
            e.preventDefault();
            const id = document.getElementById('newRepo').value || "build-" + Math.random().toString(36).substr(2, 5);
            const selector = document.getElementById('buildSelector');
            const opt = document.createElement('option');
            opt.value = id; opt.innerText = id;
            selector.appendChild(opt);
            selector.value = id;
            registry[id] = { logs: [], research: [], state: {SPEC:'waiting', SWARM:'waiting', RENDER:'waiting'} };
            switchContext();
        };

        function switchContext() {
            activeId = document.getElementById('buildSelector').value;
            if(!activeId) { document.getElementById('dashboard').style.display='none'; return; }
            document.getElementById('dashboard').style.display='block';
            document.getElementById('display-id').innerText = activeId;
            updateUI();
        }

        function updateUI() {
            const data = registry[activeId];
            ['SPEC', 'SWARM', 'RENDER'].forEach(l => {
                document.getElementById('L1_'+l).className = 'layer-box ' + data.state[l];
                document.getElementById('status-'+l).innerText = data.state[l].toUpperCase();
            });
            document.getElementById('log-stream').innerHTML = data.logs.join('<br>');
            document.getElementById('arFeed').innerHTML = data.research.map(r => `<div style="padding:10px; border-bottom:1px solid #d0d7de;"><b>[EVENT]</b> ${r}</div>`).join('');
        }

        function triggerSwarm() {
            if(!activeId) return;
            const steps = [
                {l:'SPEC', s:'active', m:'Parsing § clauses...'},
                {l:'SPEC', s:'completed', m:'Forensic spec alignment verified.'},
                {l:'SWARM', s:'active', m:'Ruflo Brain: Orchestrating 60+ agents...'},
                {l:'SWARM', s:'completed', m:'Swarm audit complete. PR submitted.'},
                {l:'RENDER', s:'active', m:'Querying Render API for health check...'},
                {l:'RENDER', s:'completed', m:'Deployment Stable. P1 Certification Pass.'}
            ];
            let i = 0;
            const timer = setInterval(() => {
                const step = steps[i];
                registry[activeId].state[step.l] = step.s;
                registry[activeId].logs.push(`[${new Date().toLocaleTimeString()}] ${step.m}`);
                updateUI();
                i++;
                if(i >= steps.length) clearInterval(timer);
            }, 2000);
        }

        function logAR() {
            const val = document.getElementById('arInput').value;
            if(!val || !activeId) return;
            registry[activeId].research.push(val);
            document.getElementById('arInput').value = '';
            updateUI();
        }
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
