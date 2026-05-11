from flask import Flask, request, jsonify
import os
import fitz  # PyMuPDF acting as the Ruflo engine
from controller import load_spec, load_smr, build_evidentia
from registry_service import registry

app = Flask(__name__)

def ruflo_transformer(pdf_path):
    """Ruflo-style PDF to Text transformation."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

@app.route('/inject_spec', methods=['POST'])
def inject_spec():
    try:
        if 'file' in request.files:
            file = request.files['file']
            raw_path = file.filename
            file.save(raw_path)
            
            print(f"[RUFLO] Ingesting PDF: {raw_path}")
            # Perform the transformation
            content = ruflo_transformer(raw_path)
            
            # Save as text for the controller to read
            spec_filename = "transformed_spec.txt"
            with open(spec_filename, "w") as f:
                f.write(content)
        else:
            data = request.get_json()
            spec_content = data.get('specification', '')
            spec_filename = "injected_text_spec.txt"
            with open(spec_filename, "w") as f:
                f.write(spec_content)
        
        registry.verify_authority("2.2")
        load_spec(spec_filename)
        load_smr()
        result = build_evidentia()
        
        return jsonify({"status": "SUCCESS", "message": "Evidentia Build Authorized via Ruflo"}), 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
