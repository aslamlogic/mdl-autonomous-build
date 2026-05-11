from flask import Flask, render_template_string, jsonify, request
import datetime

app = Flask(__name__)

@app.route('/api/calculate_tier', methods=['POST'])
def calculate_tier():
    # Forensic application of KUP v1.5 § 1.2 and § 8.4
    n_ku = request.json.get('normative_count', 0)
    e_ku = request.json.get('empirical_count', 0)
    
    ratio = n_ku / e_ku if e_ku > 0 else 0
    
    if ratio > 0.6:
        tier, model = "EXPERT", "GPT-4o / Frontier"
    elif ratio > 0.2:
        tier, model = "PROFESSIONAL", "Claude 3.5 Sonnet"
    else:
        tier, model = "STANDARD", "Llama 3-8B"
        
    return jsonify({
        "ratio": round(ratio, 2),
        "tier": tier,
        "assigned_model": model,
        "timestamp": datetime.datetime.now().strftime('%H:%M:%S')
    })

# ... Unified Sidebar HUD Logic ...
