from flask import Flask, render_template_string, jsonify, request
import datetime

app = Flask(__name__)

# Forensic Validation Layer: LWP v1.4 Variant of SMR v5.6
@app.route('/api/validate_legal_output', methods=['POST'])
def validate():
    data = request.json
    # Validation Criteria per LWP Section 10.2
    is_evidence_linked = data.get('has_citation', False) # [cite: 242]
    is_non_advisory = not data.get('makes_decision', True) # [cite: 245]
    is_structured = data.get('is_structured', False) # [cite: 232]
    
    status = "VALIDATED" if (is_evidence_linked and is_non_advisory and is_structured) else "REJECTED"
    
    return jsonify({
        "timestamp": datetime.datetime.now().strftime('%H:%M:%S'),
        "protocol": "LWP v1.4 (Subordinate to SMR v5.6)",
        "status": status,
        "action": "Proceed to Expert Tier" if status == "VALIDATED" else "Halt Output"
    })
