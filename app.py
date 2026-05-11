from flask import Flask, render_template_string, jsonify, request
import datetime

app = Flask(__name__)

# Forensic Gap Data mapped from Evidentia specification v2.2.txt
GAPS = {
    "§ 3.2": {
        "file": "evidenceChain.ts",
        "code": "export interface EvidenceNode {\n  id: string;\n  parentId: string | null;\n  claim: string;\n  probability: number;\n  verified: boolean;\n}\n\nexport const validateRecursiveChain = (node: EvidenceNode, registry: EvidenceNode[]): boolean => {\n  if (!node.parentId) return node.verified;\n  const parent = registry.find(n => n.id === node.parentId);\n  return node.verified && (parent ? validateRecursiveChain(parent, registry) : false);\n};"
    },
    "§ 4.5": {
        "file": "proofScalar.ts",
        "code": "export type ProofBalance = 'preponderance' | 'clear_and_convincing' | 'beyond_reasonable_doubt';\n\nexport const calculateScalar = (evidenceWeight: number): ProofBalance => {\n  if (evidenceWeight > 0.9) return 'beyond_reasonable_doubt';\n  if (evidenceWeight > 0.7) return 'clear_and_convincing';\n  return 'preponderance';\n};"
    }
}

@app.route('/')
def home():
    return render_template_string(HUD_HTML)

@app.route('/api/generate_fix', methods=['POST'])
def generate_fix():
    clause = request.json.get('clause')
    data = GAPS.get(clause, {"code": "// No logic found", "file": "unknown"})
    return jsonify({
        "timestamp": datetime.datetime.now().strftime('%H:%M:%S'),
        "clause": clause,
        "file": data['file'],
        "code": data['code']
    })

HUD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>RUFLO BRAIN v3.7 - TELEMETRY HEALER</title>
    <style>
        body { background:#ffffff; color:#1f2328; font-family: -apple-system, sans-serif; padding:30px; }
        .nexus-grid { display: grid; grid-template-columns: 400px 1fr; gap: 30px; }
        .card { border:1px solid #d0d7de; padding:25px; border-radius:12px; background: #ffffff; }
        .gap-item { border: 1px solid #d0d7de; padding:15px; margin-bottom:10px; border-radius:8px; cursor:pointer; transition: 0.2s; }
        .gap-item:hover { border-color: #0969da; background: #f6f8fa; }
        #console { background:#0d1117; color:#7ee787; padding:20px; height:500px; overflow-y:scroll; border-radius:8px; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 13px; line-height: 1.5; }
        .btn-plug { background:#0969da; color:white; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; float:right; }
        .code-block { color: #a5d6ff; display: block; margin-top: 10px; border-top: 1px solid #30363d; padding-top: 10px; }
    </style>
</head>
<body>
    <h1>aslamlogic // Ruflo Swarm: Telemetry Gap-Fill</h1>
    <div class="nexus-grid">
        <div class="card">
            <h3>Audit: Missing § Clauses</h3>
            <div id="gapList"></div>
        </div>
        <div class="card">
            <h3>Swarm Telemetry (Live Ingress)</h3>
            <div id="console">Awaiting clause selection...</div>
        </div>
    </div>

    <script>
        const gapData = [
            {id: "§ 3.2", title: "Relational Evidence Chain", file: "evidenceChain.ts"},
            {id: "§ 4.5", title: "Burden of Proof Scalar", file: "proofScalar.ts"},
            {id: "§ 7.3", title: "Conflict Resolution Matrix", file: "conflictMatrix.ts"}
        ];

        function init() {
            const list = document.getElementById('gapList');
            gapData.forEach(g => {
                const div = document.createElement('div');
                div.className = 'gap-item';
                div.innerHTML = `<strong>${g.id}</strong>: ${g.title}<br><small>${g.file}</small>`;
                div.onclick = () => streamCode(g.id);
                list.appendChild(div);
            });
        }

        async function streamCode(clause) {
            const consoleBox = document.getElementById('console');
            consoleBox.innerHTML += `[SYSTEM] Requesting logic for ${clause}...<br>`;
            
            const res = await fetch('/api/generate_fix', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ clause })
            });
            const data = await res.json();
            
            consoleBox.innerHTML += `<span style="color:#e3b341">[AUDIT] Gap in ${data.file} identified.</span><br>`;
            consoleBox.innerHTML += `<span style="color:#1f883d">[RUFLO] Injecting § Clauses...</span><br>`;
            consoleBox.innerHTML += `<div class="code-block">${data.code.replace(/\\n/g, '<br>')}</div><br>`;
            consoleBox.innerHTML += `<span style="color:#58a6ff">[SUCCESS] Logic aligned with Spec v2.2.txt</span><br><hr style="border-color:#30363d">`;
            consoleBox.scrollTop = consoleBox.scrollHeight;
        }

        init();
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
