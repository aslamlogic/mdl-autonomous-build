from flask import Flask, request, render_template_string
import fitz
import os

app = Flask(__name__)

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>FIS Nexus Drop Zone</title></head>
<body style="font-family:sans-serif; padding:50px; background-color:#f8f9fa;">
    <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <h1>FIS Nexus Drop Zone</h1>
        <p>Windows Environment Active</p>
        <form action="/inject_spec" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required style="margin-bottom: 20px;">
            <br>
            <button type="submit" style="background:#007bff; color:white; border:none; padding:10px 20px; border-radius:4px; cursor:pointer;">Inject PDF</button>
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
    if 'file' not in request.files:
        return "No file detected", 400
    
    file = request.files['file']
    stream = file.read()
    
    # Ruflo Extraction with explicit text flag
    doc = fitz.open(stream=stream, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text("text")
        
    if not full_text.strip():
        return "<h1>Error</h1><p>Ruflo found NO text layer. This PDF may be a scanned image.</p>"
        
    return f"<h1>Ruflo Success</h1><p>Extracted {len(full_text)} characters.</p><pre style='background:#eeeeee; padding:20px; white-space: pre-wrap;'>{full_text[:5000]}</pre>"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
