from flask import Flask, request, render_template_string
import pytesseract
from pdf2image import convert_from_bytes
import os

app = Flask(__name__)

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>RUFLO GATEWAY - OPTIMIZED</title></head>
<body style="font-family:sans-serif; padding:50px; background:#0d1117; color:#c9d1d9;">
    <div style="max-width:800px; margin:auto; border:1px solid #30363d; padding:30px; border-radius:10px;">
        <h1>Ruflo Gateway: Evidentia Ingestion</h1>
        <p style="color:#8b949e;">Status: Optimized for Render Substrate</p>
        <form action="/inject_spec" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required>
            <br><br>
            <button type="submit" style="background:#238636; color:white; border:none; padding:10px 20px; border-radius:6px; cursor:pointer;">START LIGHT INGESTION</button>
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
    file_bytes = request.files['file'].read()
    
    # SYSTEM OPTIMIZATION: Only process first 3 pages to avoid 502 Timeout
    images = convert_from_bytes(file_bytes, first_page=1, last_page=3)
    full_text = ""
    
    for i, image in enumerate(images):
        page_text = pytesseract.image_to_string(image)
        full_text += f"\n--- Page {i+1} ---\n" + page_text
        
    return f'''
    <h1>Success: Ingestion Stable</h1>
    <p>Swarm has identified the Evidentia Core requirements from first 3 pages.</p>
    <div style="background:#161b22; color:#58a6ff; padding:20px; border:1px solid #30363d; height:500px; overflow-y:scroll; font-family:monospace; white-space:pre-wrap;">
        {full_text}
    </div>
    '''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
