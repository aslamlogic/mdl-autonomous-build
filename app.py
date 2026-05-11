from flask import Flask, render_template_string, jsonify, request
import datetime

app = Flask(__name__)

@app.route('/api/forensic_compare', methods=['POST'])
def compare():
    # Simulation based on Knowledge Unit Protocol v1.5 structural rules
    case_data = request.json.get('data', '')
    
    # 1. Swarm Heuristic
    swarm_complexity = len(case_data.split()) / 500 # Simple word count logic
    
    # 2. Protocol Forensic (Simulated extraction of discrete claims)
    normative_kus = 18  # Extracted § Clauses from Spec v2.2
    empirical_kus = 12  # Extracted facts from Case
    ratio = normative_kus / empirical_kus
    protocol_complexity = (ratio * 10) / 2 # KUP v1.5 weighted scalar
    
    return jsonify({
        "timestamp": datetime.datetime.now().strftime('%H:%M:%S'),
        "swarm_score": round(swarm_complexity, 1),
        "protocol_score": round(protocol_complexity, 1),
        "tier": "EXPERT" if ratio > 0.6 else "PROFESSIONAL",
        "model": "GPT-4o (Frontier)" if ratio > 0.6 else "Sonnet 3.5"
    })

# ... HUD Template with Comparison Graphs ...
