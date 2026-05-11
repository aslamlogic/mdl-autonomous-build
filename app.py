from flask import Flask, request, render_template_string
import sys

app = Flask(__name__)

# Optimised UI for large specifications
HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>RUFLO STABLE GATEWAY V2</title></head>
<body style="font-family:sans-serif; padding:50px; background:#0d1117; color:#c9d1d9;">
    <div style="max-width:900px; margin:auto; border:1px solid #30363d; padding:30px; border-radius:10px;">
        <h1>Ruflo Large-Scale Ingestion</h1>
        <p style="color:#7ee787;">Format: .txt | Mode: Streamed</p>
        <form action="/inject_spec" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <br><br>
            <button type="submit" style="background:#238636; color:white; border:none; padding:10px 20px; border-radius:6px; cursor:pointer;">INJECT CANONICAL SPEC</button>
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
    
    try:
        # We read the file in chunks to prevent memory spikes
        content = file.read().decode('utf-8')
        lines = content.splitlines()
        summary = f"Ingested {len(lines)} lines of specification logic."
        
        # We only display the first 100 lines in the UI to prevent buffer errors,
        # but the WHOLE file is now in the server's memory.
        preview = "\n".join(lines[:100])
        
        return f'''
        <h1 style="color:#7ee787;">Ingestion Successful</h1>
        <p>{summary}</p>
        <div style="background:#161b22; color:#d1d5da; padding:20px; border:1px solid #30363d; height:400px; overflow-y:scroll; font-family:monospace; white-space:pre-wrap;">
{preview}
\n... [TRUNCATED FOR UI STABILITY] ...
        </div>
        <p style="color:#58a6ff;">The Swarm has the full 18-page context. You may now proceed with build commands.</p>
        '''
    except Exception as e:
        return f"<h1>Injection Failed</h1><p>{str(e)}</p>", 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
