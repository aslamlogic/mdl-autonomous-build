from flask import Flask, request, render_template_string
import fitz
import pdfplumber
import os
import requests

app = Flask(__name__)

# THE TETHER: Connecting the Swarm to the Cloud
RENDER_KEY = os.getenv('RENDER_API_KEY')
GITHUB_APP_TOKEN = os.getenv('GITHUB_TOKEN')

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>RUFLO MASTER ORCHESTRATOR</title></head>
<body style="font-family:sans-serif; padding:50px; background:#0d1117; color:#c9d1d9;">
    <div style="max-width:800px; margin:auto; border:1px solid #30363d; padding:30px; border-radius:10px;">
        <h1>Ruflo Autonomous Nexus</h1>
        <p style="color:#8b949e;">Status: Tethered | Environment: Multi-Agent Ready</p>
        <form action="/inject_spec" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required>
            <br><br>
            <button type="submit" style="background:#238636; color:white; border:none; padding:10px 20px; border-radius:6px; cursor:pointer; font-weight:bold;">INITIALIZE SWARM INGESTION</button>
        </form>
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/inject_spec', methods=['POST'])
def inject():
    file = request.files['file']
    file_bytes = file.read()
    
    # AGENT 1: Standard Scraper (PyMuPDF)
    text = ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text("text")
    except:
        pass

    # AGENT 2: The Evaluator (Detecting "Squares" or Encoding Errors)
    # If text is empty or contains non-English garbage, trigger Self-Healing
    if len(text.strip()) < 50 or "" in text or not any(c.isalpha() for c in text[:100]):
        print("SWARM ALERT: Encoding failure detected. Switching to Agent 3 (pdfplumber)...")
        # AGENT 3: The Repair Scraper (Handles CID/Non-Standard Fonts)
        with pdfplumber.open(request.files['file']) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

    return f'''
    <h1>Ruflo Transformation Engine</h1>
    <p>Success Level: Self-Healed</p>
    <div style="background:#161b22; color:#58a6ff; padding:20px; border:1px solid #30363d; height:500px; overflow-y:scroll; font-family:monospace;">
        {text[:10000] if text else "FATAL: All agents failed to read text layer. PDF is likely an image scan."}
    </div>
    '''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
