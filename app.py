from flask import Flask, render_template_string, jsonify, request
import datetime

app = Flask(__name__)

# Forensic Data remains persistent
GAPS = {
    "§ 5.8": {"file": "hearsayFilter.ts", "code": "export const hearsayCheck = (s: string) => s.includes('allegedly');"},
    "§ 6.2": {"file": "custody.ts", "code": "export const hashEvidence = (d: any) => ({...d, hash: '0xABC'});"}
}

@app.route('/')
def home():
    return render_template_string(HUD_HTML)

HUD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>RUFLO UNIFIED WORKSPACE v3.9</title>
    <style>
        body { background:#f6f8fa; color:#1f2328; font-family: -apple-system, sans-serif; display: flex; height: 100vh; margin: 0; }
        #sidebar { width: 280px; background: #ffffff; border-right: 1px solid #d0d7de; padding: 25px; }
        #main-content { flex: 1; padding: 40px; overflow-y: auto; }
        .nav-item { padding: 15px; cursor: pointer; border-radius: 8px; margin-bottom: 10px; font-weight: bold; }
        .nav-item:hover { background: #f3f4f6; }
        .nav-active { background: #0969da !important; color: white; }
        .card { background: white; border: 1px solid #d0d7de; padding: 30px; border-radius: 12px; margin-bottom: 20px; }
        #telemetry-box { background:#0d1117; color:#7ee787; padding:20px; height:400px; border-radius:8px; overflow-y:scroll; font-family:monospace; }
        .view-panel { display: none; }
        .view-active { display: block; }
    </style>
</head>
<body>
    <div id="sidebar">
        <h2 style="font-size:18px;">aslamlogic // Ruflo</h2>
        <div class="nav-item nav-active" onclick="show('home', this)">1. INGRESS (HOME)</div>
        <div class="nav-item" onclick="show('telemetry', this)">2. SWARM TELEMETRY</div>
        <div class="nav-item" onclick="show('ledger', this)">3. FORENSIC LEDGER</div>
    </div>

    <div id="main-content">
        <div id="view-home" class="view-panel view-active">
            <h1>Workspace Ingress</h1>
            <div class="card">
                <h3>Initialize Specification</h3>
                <input type="file" id="specFile">
                <button style="margin-top:15px; padding:12px; background:#1f883d; color:white; border:none; border-radius:6px; cursor:pointer; width:100%;">
                    LAUNCH BUILD INSTANCE
                </button>
            </div>
            <div class="card">
                <h3>Context Switching</h3>
                <p>Targeting: <strong>evidentia-app</strong></p>
                <button style="background:#0969da; color:white; border:none; padding:12px; border-radius:6px; width:100%;">REPAIR / UPDATE EXISTING</button>
            </div>
        </div>

        <div id="view-telemetry" class="view-panel">
            <h1>Swarm Telemetry</h1>
            <div class="card" id="telemetry-box">
                [SYSTEM] Awaiting forensic audit command...
            </div>
        </div>

        <div id="view-ledger" class="view-panel">
            <h1>Forensic Ledger</h1>
            <div class="card">
                <p><strong>[2026-05-11]</strong>: Successfully mapped 12 § clauses to evidentia-app substrate.</p>
            </div>
        </div>
    </div>

    <script>
        function show(viewId, el) {
            document.querySelectorAll('.view-panel').forEach(v => v.classList.remove('view-active'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('nav-active'));
            document.getElementById('view-' + viewId).classList.add('view-active');
            el.classList.add('nav-active');
        }
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
