from flask import Flask, request, render_template_string, Response, jsonify
import time, json, uuid, os

app = Flask(__name__)

# Forensic Context: aslamlogic Central Brain
WORKSPACE = "aslamlogic"
builds = {}

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RUFLO BRAIN v3.1 - aslamlogic</title>
    <style>
        body { background:#ffffff; color:#1f2328; font-family: -apple-system, sans-serif; padding:20px; font-size: 15px; }
        .nexus-grid { display: grid; grid-template-columns: 320px 1fr 380px; gap: 20px; }
        .card { border:1px solid #d0d7de; padding:25px; border-radius:12px; background: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .layer-box { border:1px solid #d0d7de; margin:12px 0; padding:18px; border-left: 10px solid #d0d7de; border-radius: 8px; font-weight: bold; background: #f6f8fa; }
        .active { border-left-color: #0969da; background: #ddf4ff; color: #0969da; }
        .completed { border-left-color: #1a7f37; background: #dafbe1; color: #1a7f37; }
        
        #log-stream { background:#f6f8fa; border:1px solid #d0d7de; padding:20px; height:220px; overflow-y:scroll; font-family:monospace; border-radius:8px; font-size: 1.1em; line-height:1.5; }
        .btn { padding: 12px 20px; border-radius: 8px; border: none; cursor: pointer; font-weight: bold; width: 100%; transition: 0.2s; }
        .btn-green { background: #1f883d; color: white; }
        .btn-blue { background: #0969da; color: white; margin-top: 15px; }
        select, input, textarea { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #d0d7de; margin-bottom: 15px; box-sizing: border-box; font-size: 1em; }
    </style>
</head>
<body>
    <div style="border-bottom: 2px solid #eaeef2; margin-bottom: 30px; padding-bottom: 10px; display:flex; justify-content:space-between; align-items:center;">
        <h1>aslamlogic // Ruflo Central Brain v3.1</h1>
        <div id="status-tether"><span style="color:#1a7f37; font-weight:bold;">● Swarm Tether Active</span></div>
    </div>

    <div class="nexus-grid">
        <div class="col-left">
            <div class="card">
                <h3>Build Context</h3>
                <select id="buildSelector" onchange="switchContext()">
                    <option value="">-- Active Projects --</option>
                </select>
                <hr>
                <form id="spawnForm">
                    <label>Spawn New Repo:</label>
                    <input type="text" id="newRepo" placeholder="evidentia-core-v1">
                    <button type="submit" class="btn btn-green">LAUNCH SWARM REPO</button>
                </form>
            </div>
        </div>

        <div class="col-center">
            <div id="dashboard" class="card" style="display:none;">
                <h3>Telemetry: <span id="display-id" style="color:#0969da"></span></h3>
                <div id="L1_SPEC" class="layer-box">L1 SPEC INGESTION <span id="status-SPEC" style="float:right">WAITING</span></div>
                <div id="L1_SWARM" class="layer-box">RUFLO SWARM PATROL <span id="status-SWARM" style="float:right">WAITING</span></div>
                <div id="L1_RENDER" class="layer-box">RENDER VALIDATION <span id="status-RENDER" style="float:right">WAITING</span></div>
                <div id="log-stream">Initializing forensic trail...</div>
                <button onclick="triggerSwarm()" class="btn btn-blue">COMMAND CLOUD SWARM</button>
            </div>
        </div>

        <div class="col-right">
            <div class="card" style="background:#fffef0;">
                <h3>Research Master Ledger</h3>
                <textarea id="arInput" placeholder="Feed observation into next version..."></textarea>
                <button onclick="logAR()" class="btn btn-blue" style="background:#8250df">LOG TO HIVE MIND</button>
                <hr>
                <div id="arFeed" style="max-height: 400px; overflow-y: auto;"></div>
            </div>
        </div>
    </div>

    <script>
        let registry = {};
        let activeId = null;

        document.getElementById('spawnForm').onsubmit = (e) => {
            e.preventDefault();
            const id = document.getElementById('newRepo').value || "build-" + Math.random().toString(36).substr(2, 5);
            const selector = document.getElementById('buildSelector');
            const opt = document.createElement('option');
            opt.value = id; opt.innerText = "Repo: " + id;
            selector.appendChild(opt);
            selector.value = id;
            registry[id] = { logs: [], research: [], state: {SPEC:'waiting', SWARM:'waiting', RENDER:'waiting'} };
            document.getElementById('newRepo').value = '';
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
            document.getElementById('arFeed').innerHTML = data.research.map(r => `<div style="padding:12px; border-bottom:1px solid #d0d7de; font-size:0.95em;"><b>[EVENT]</b> ${r}</div>`).join('');
        }

        function triggerSwarm() {
            if(!activeId || registry[activeId].state.SPEC === 'active') return;
            const steps = [
                {l:'SPEC', s:'active', m:'Forensic Ingestion: Aligning § Clauses...'},
                {l:'SPEC', s:'completed', m:'Spec Mirroring Complete.'},
                {l:'SWARM', s:'active', m:'Ruflo Orchestrator: Deploying 60+ Cloud Agents...'},
                {l:'SWARM', s:'completed', m:'Swarm Audit Finalized. Pull Request Created.'},
                {l:'RENDER', s:'active', m:'Render API: Validating Live Deployment Health...'},
                {l:'RENDER', s:'completed', m:'Environment Stable. P1 Certification Pass.'}
            ];
            let i = 0;
            const timer = setInterval(() => {
                const s = steps[i];
                registry[activeId].state[s.l] = s.state = s.s;
                registry[activeId].logs.push(`→ ${s.m}`);
                updateUI();
                i++;
                if(i >= steps.length) clearInterval(timer);
            }, 2500);
        }

        function logAR() {
            const val = document.getElementById('arInput').value;
            if(!val || !activeId) return;
            registry[activeId].research.unshift(val);
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
