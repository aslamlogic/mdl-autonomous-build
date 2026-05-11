from flask import Flask, request, render_template_string
from tika import parser
import io

app = Flask(__name__)

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>RUFLO UNIVERSAL GATEWAY</title></head>
<body style="font-family:sans-serif; padding:50px; background:#0d1117; color:#c9d1d9;">
    <div style="max-width:800px; margin:auto; border:1px solid #30363d; padding:30px; border-radius:10px;">
        <h1>Ruflo Universal Ingestion</h1>
        <p style="color:#58a6ff;">Engine: Apache Tika Swarm Logic</p>
        <form action="/inject_spec" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <br><br>
            <button type="submit" style="background:#238636; color:white; border:none; padding:10px 20px; border-radius:6px; cursor:pointer;">UNIVERSAL INGEST</button>
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
    file_contents = file.read()
    
    # Apache Tika: The "Universal Wheel" for file conversion
    parsed = parser.from_buffer(file_contents)
    text = parsed.get("content", "")
    metadata = parsed.get("metadata", {})
    
    if not text or not text.strip():
        return "<h1>Ingestion Failure</h1><p>The universal engine could not parse this file type.</p>"
        
    return f'''
    <h1>Ruflo Universal Success</h1>
    <p>File Type: {metadata.get('Content-Type', 'Unknown')}</p>
    <div style="background:#161b22; color:#7ee787; padding:20px; border:1px solid #30363d; height:500px; overflow-y:scroll; font-family:monospace; white-space:pre-wrap;">
        {text[:20000]}
    </div>
    '''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
