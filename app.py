from flask import Flask, render_template_string, jsonify, request, send_from_directory
import datetime
import subprocess
import os

app = Flask(__name__)

# Forensic Validation Layer: LWP v1.4 Variant of SMR v5.6
@app.route('/api/validate_legal_output', methods=['POST'])
def validate():
    data = request.json
    is_evidence_linked = data.get('has_citation', False)
    is_non_advisory = not data.get('makes_decision', True)
    is_structured = data.get('is_structured', False)
    
    status = "VALIDATED" if (is_evidence_linked and is_non_advisory and is_structured) else "REJECTED"
    
    return jsonify({
        "timestamp": datetime.datetime.now().strftime('%H:%M:%S'),
        "protocol": "LWP v1.4 (Subordinate to SMR v5.6)",
        "status": status,
        "action": "Proceed to Expert Tier" if status == "VALIDATED" else "Halt Output"
    })

# -----------------------------
# Serve static UI (from frontend/static)
# -----------------------------
UI_FOLDER = os.path.join(os.path.dirname(__file__), 'frontend', 'static')
if os.path.exists(UI_FOLDER):
    @app.route('/ui/<path:filename>')
    def serve_ui(filename):
        return send_from_directory(UI_FOLDER, filename)

    @app.route('/')
    def serve_index():
        index_path = os.path.join(UI_FOLDER, 'upload_dashboard.html')
        if os.path.exists(index_path):
            return send_from_directory(UI_FOLDER, 'upload_dashboard.html')
        return jsonify({"message": "UI index not found, but API is available"}), 200

# -----------------------------
# Build trigger endpoint (for Evidentia and PAIOS)
# -----------------------------
@app.route('/api/build/<product>', methods=['POST'])
def trigger_build(product):
    if product not in ['evidentia', 'paios']:
        return jsonify({"error": "Invalid product. Use 'evidentia' or 'paios'"}), 400
    
    try:
        # Run controller.py with product argument (adjust flags as needed)
        result = subprocess.run(
            ['python', '/app/controller.py', '--product', product],
            capture_output=True,
            text=True,
            timeout=300
        )
        return jsonify({
            "product": product,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Build timed out after 300 seconds"}), 408
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Health check
# -----------------------------
@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
