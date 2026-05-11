from flask import Flask, request, render_template_string
import pdfplumber
import io

app = Flask(__name__)

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>RUFLO FINAL GATEWAY</title></head>
<body style="font-family:sans-serif; padding:50px; background:#0d1117; color:#c9d1d9;">
    <div style="max-width:800px; margin:auto; border:1px solid #30363d; padding:30px; border-radius:10px;">
        <h1>Ruflo Autonomous Ingestion</h1>
        <p style="color:#58a6ff;">Substrate: Layout-Aware Ingestion Active</p>
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
    
    # Layout Ingestion: Bypasses CID locks by analyzing the character placement
    full_text = ""
    with pdfplumber.open(io.BytesIO(file.read())) as pdf:
        for page in pdf.pages:
            # Extract text with horizontal/vertical character mapping
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if text:
                full_text += text + "\n"

    if not full_text.strip():
        return "<h1>Error</h1><p>Layout engine returned no text. PDF may be an image.</p>"
        
    return f'''
    <h1>Ingestion Success</h1>
    <div style="background:#161b22; color:#7ee787; padding:20px; border:1px solid #30363d; height:500px; overflow-y:scroll; font-family:monospace; white-space:pre-wrap;">
        {full_text[:20000]}
    </div>
    '''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
