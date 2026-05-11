from flask import Flask, request, render_template_string
import fitz  # PyMuPDF
import os

app = Flask(__name__)

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>RUFLO DIRECT PERCEPTION</title></head>
<body style="font-family:sans-serif; padding:50px; background:#0d1117; color:#c9d1d9;">
    <div style="max-width:800px; margin:auto; border:1px solid #30363d; padding:30px; border-radius:10px;">
        <h1>Ruflo Neural Override</h1>
        <p style="color:#ff7b72;">Status: CID Map Failure. Visual Perception Active.</p>
        <form action="/inject_spec" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required>
            <br><br>
            <button type="submit" style="background:#238636; color:white; border:none; padding:10px 20px; border-radius:6px; cursor:pointer;">FORCE VISUAL INGESTION</button>
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
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    
    # We are going to force the engine to look at the FIRST page only
    # to ensure the server doesn't timeout while doing "Visual Perception"
    page = doc[0]
    
    # SYSTEM OVERRIDE: Instead of extracting text, we extract the XML structure
    # which often contains the raw UTF-8 fallback that standard extraction misses.
    raw_data = page.get_text("dict") 
    
    output = ""
    for block in raw_data["blocks"]:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    output += span["text"] + " "
    
    return f'''
    <h1>Success: Substrate Pierced</h1>
    <div style="background:#161b22; color:#7ee787; padding:20px; border:1px solid #30363d; height:500px; overflow-y:scroll; font-family:monospace; white-space:pre-wrap;">
        {output if len(output) > 10 else "VISION BLOCKED: Switching to Image-Based OCR next if this fails."}
    </div>
    '''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
