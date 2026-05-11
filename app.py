from flask import Flask, request, render_template_string
from tika import parser
import os

app = Flask(__name__)

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RUFLO UNIVERSAL GATEWAY</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 50px; background: #0d1117; color: #c9d1d9; }
        .container { max-width: 800px; margin: auto; border: 1px solid #30363d; padding: 30px; border-radius: 12px; background: #161b22; }
        h1 { color: #58a6ff; }
        button { background: #238636; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        button:hover { background: #2ea043; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Ruflo Universal Ingestion</h1>
        <p>Powered by Apache Tika: The Industrial Standard.</p>
        <form action="/inject_spec" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required style="margin-bottom: 20px;">
            <br>
            <button type="submit">START UNIVERSAL INGESTION</button>
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
    
    # Universal Extraction: No more reinventing the wheel.
    parsed = parser.from_buffer(file_bytes)
    content = parsed.get("content", "")
    metadata = parsed.get("metadata", {})

    if not content or not content.strip():
        return "<h1>Ingestion Error</h1><p>Tika failed to extract text from the substrate.</p>"

    return f'''
    <h1>Ingestion Success</h1>
    <p>Target Type: {metadata.get('Content-Type', 'Unknown')}</p>
    <div style="background:#0d1117; color:#7ee787; padding:20px; border:1px solid #30363d; height:500px; overflow-y:scroll; font-family:monospace; white-space:pre-wrap;">
        {content}
    </div>
    '''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
