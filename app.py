from flask import Flask, request, jsonify
import os
import fitz  # Ruflo PDF Parsing Engine
from controller import load_spec, load_smr, build_evidentia
from registry_service import registry

app = Flask(__name__)

def ruflo_extract(file_path):
    """Internal Ruflo logic to convert PDF binary to technical text."""
    doc = fitz.open(file_path)
    return "".join([page.get_text() for page in doc])

@app.route('/inject_spec', methods=['POST'])
def inject_spec():
    try:
        # Scenario A: File Drop (PDF)
        if 'file' in request.files:
            file = request.files['file']
            save_path = f"raw_{file.filename}"
            file.save(save_path)
            content = ruflo_extract(save_path)
        
        # Scenario B: Manual Text/JSON Ingestion
        else:
            data = request.get_json(silent=True) or {}
            content = data.get('specification', request.form.get('specification', ''))
        
        if not content:
            return jsonify({"status": "ERROR", "message": "No specification data detected."}), 400

        # Create the 'Truth Source' file for the controller
        spec_filename = "active_specification.txt"
        with open(spec_filename, "w") as f:
            f.write(content)
        
        # Trigger Factory Build
        registry.verify_authority("2.2")
        load_spec(spec_filename)
        load_smr()
        result = build_evidentia()
        
        return jsonify({"status": "SUCCESS", "message": "Evidentia Build Authorized via Ruflo", "trace": result}), 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
