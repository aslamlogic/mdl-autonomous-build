from flask import Flask, request, render_template_string
import fitz  # Ruflo Engine
import os

app = Flask(__name__)

# The Visual Interface
HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>FIS Nexus Drop Zone</title>
    <style>
        body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; padding: 50px; }
        .drop-zone { border: 2px dashed #007bff; padding: 40px; border-radius: 10px; width: 300px; text-align: center; }
    </style>
</head>
<body>
    <h1>FIS Nexus Drop Zone</h1>
    <div class="drop-zone">
        <form action="/inject_spec" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required>
            <br><br>
            <button type="submit" style="padding: 10px 20px; cursor: pointer;">Inject PDF</button>
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
        return "No file uploaded", 400
    file = request.files['file']
    
    # Ruflo Extraction
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
        
    return f"<h1>Ruflo Success</h1><p>Extracted {len(text)} characters from Evidentia Spec.</p><pre>{text[:2000]}...</pre>"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
