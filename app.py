from flask import Flask, request, render_template_string
from pdfminer.high_level import extract_text
import io

app = Flask(__name__)

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>RUFLO LOCKPICK - ACTIVE</title></head>
<body style="font-family:sans-serif; padding:50px; background:#0d1117; color:#c9d1d9;">
    <div style="max-width:800px; margin:auto; border:1px solid #30363d; padding:30px; border-radius:10px;">
        <h1>Ruflo Autonomous Gateway</h1>
        <p style="color:#58a6ff;">Mode: Deep Substrate Extraction (Lockpick)</p>
        <form action="/inject_spec" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required>
            <br><br>
            <button type="submit" style="background:#238636; color:white; border:none; padding:10px 20px; border-radius:6px; cursor:pointer;">INJECT SPECIFICATION</button>
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
    # pdfminer.six works by directly analyzing character streams
    # It is the best at solving the "Squares" without needing OCR
    text = extract_text(io.BytesIO(file.read()))
    
    if not text.strip():
        return "<h1>Error</h1><p>Substrate could not find a text layer.</p>"
        
    return f'''
    <h1>Ruflo Ingestion Success</h1>
    <div style="background:#161b22; color:#7ee787; padding:20px; border:1px solid #30363d; height:500px; overflow-y:scroll; font-family:monospace; white-space:pre-wrap;">
        {text[:15000]}
    </div>
    '''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
