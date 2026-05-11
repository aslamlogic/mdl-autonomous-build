from flask import Flask, request, render_template_string, Response, jsonify
import time, json, uuid

app = Flask(__name__)

# Concurrent Build Storage
active_builds = {}
research_ledger = []

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RUFLO NEXUS v2.4 - MULTI-BUILD FACTORY</title>
    <style>
        body { background:#ffffff; color:#1f2328; font-family: -apple-system, sans-serif; padding:20px; display: flex; gap: 20px; font-size: 14px; }
        .main-panel { flex: 2; border:1px solid #d0d7de; padding:20px; border-radius:12px; }
        .research-panel { flex: 1; display: flex; flex-direction: column; gap: 15px; }
        .build-card { border:1px solid #d0d7de; margin:10px 0; padding:15px; border-radius:8px; background: #f6f8fa; }
        .progress-bar { height: 10px; background: #eaeef2; border-radius: 5px; overflow: hidden; margin-top: 10px; }
        .progress-fill { height: 100%; background: #0969da; width: 0%; transition: width 0.5s; }
        .ledger-box { border:1px solid #d0d7de; padding:15px; border-radius:12px; background: #fffef0; max-height: 500px; overflow-y: auto; }
        .btn-green { background:#1f883d; color:white; border:none; padding:10px 20px; border-radius:6px; cursor:pointer; font-weight: bold; }
        .status-tag { font-size: 0.8em; padding: 2px 6px; border-radius: 4px; background: #ddf4ff; color: #0969da; float: right; }
    </style>
</head>
<body>
    <div class="main-panel">
        <h1>Multi-Build Factory Nexus v2.4</h1>
        <div class="build-card" style="background:#f6f8fa; border: 2px dashed #d0d7de;">
            <h3>Initialize New Build</h3>
            <form id="uploadForm">
                <input type="file" name="file" required>
                <button type="submit" class="btn-green">START NEW INSTANCE</button>
            </form>
        </div>
        <div id="active-builds-container">
            <h3>Active Build Queue</h3>
            </div>
    </div>

    <div class="research-panel">
        <div class="ledger-box">
            <h3>Global Research Ledger</h3>
            <div id="research-feed"></div>
        </div>
    </div>

    <script>
        const form = document.getElementById('uploadForm');
        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const res = await fetch('/start_build', { method: 'POST', body: formData });
            const { build_id } = await res.json();
            createBuildCard(build_id);
            listenToBuild(build_id);
        };

        function createBuildCard(id) {
            const container = document.getElementById('active-builds-container');
            const card = document.createElement('div');
            card.className = 'build-card';
            card.id = 'build-' + id;
            card.innerHTML = `
                <strong>Instance: ${id}</strong> <span class="status-tag" id="status-${id}">INITIALIZING</span>
                <div class="progress-bar"><div id="progress-${id}" class="progress-fill"></div></div>
                <div id="log-${id}" style="font-family:monospace; font-size:11px; margin-top:10px; color:#57606a;"></div>
            `;
            container.prepend(card);
        }

        function listenToBuild(id) {
            const eventSource = new EventSource('/stream/' + id);
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const progress = document.getElementById('progress-' + id);
                const status = document.getElementById('status-' + id);
                const log = document.getElementById('log-' + id);
                
                progress.style.width = data.percent + '%';
                status.innerText = data.layer;
                log.innerHTML = data.msg;
                
                if(data.research) {
                    const feed = document.getElementById('research-feed');
                    const entry = document.createElement('div');
                    entry.style.borderBottom = "1px solid #d0d7de";
                    entry.innerHTML = `<small style="color:#8250df">[${id}]</small> ${data.research}`;
                    feed.prepend(entry);
                }
                if(data.percent >= 100) eventSource.close();
            };
        }
    </script>
</body>
</html>
'''

@app.route('/start_build', methods=['POST'])
def start_build():
    build_id = str(uuid.uuid4())[:8]
    return jsonify({"build_id": build_id}), 200

@app.route('/stream/<build_id>')
def stream(build_id):
    def generate():
        steps = [
            {"layer": "SPEC", "percent": 25, "msg": "Ingesting Substrate...", "research": "Substrate Verified."},
            {"layer": "GOV", "percent": 50, "msg": "Governance Audit...", "research": "Rules Mapped."},
            {"layer": "GEN", "percent": 75, "msg": "Generating Schema...", "research": "SQL Initialized."},
            {"layer": "DONE", "percent": 100, "msg": "BUILD COMPLETE.", "research": "P1 Certification Ready."}
        ]
        for step in steps:
            yield f"data: {json.dumps(step)}\\n\\n"
            time.sleep(3)
    return Response(generate(), mimetype='text/event-stream')

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
