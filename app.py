from flask import Flask, request, jsonify
import os
from controller import load_spec, load_smr, build_evidentia
from registry_service import registry

app = Flask(__name__)

@app.route('/inject_spec', methods=['POST'])
def inject_spec():
    try:
        # Handle the Drop Zone File
        if 'file' in request.files:
            file = request.files['file']
            spec_filename = file.filename
            file.save(spec_filename)
        else:
            # Handle Manual Text
            data = request.get_json()
            spec_content = data.get('specification', '')
            spec_filename = "injected_text_spec.txt"
            with open(spec_filename, "w") as f:
                f.write(spec_content)
        
        registry.verify_authority("2.2")
        load_spec(spec_filename)
        load_smr()
        result = build_evidentia()
        
        return jsonify({"status": "SUCCESS", "message": f"Build Initiated using {spec_filename}"}), 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
