import os, sys, subprocess, time, json, uuid, sqlite3, pathlib, asyncio
from typing import List

# 1. AUTO-DEPS
REQUIRED = ["fastapi", "uvicorn", "aiofiles", "python-multipart"]
try:
    from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
    from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn, aiofiles
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", *REQUIRED])
    from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
    from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn, aiofiles

# 2. FILE SYSTEM SETUP
BASE_DIR = pathlib.Path.cwd()
FRONTEND_DIR = BASE_DIR / "frontend" / "static"
SPECS_DIR = BASE_DIR / "specs"
DB_FILE = BASE_DIR / "mdl_factory.db"
for d in [FRONTEND_DIR, SPECS_DIR]: d.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
conn.execute("CREATE TABLE IF NOT EXISTS builds (id TEXT PRIMARY KEY, title TEXT, status TEXT, logs TEXT, created_at REAL)")

# 3. GENERATE FRONTEND
HTML = r"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>MDL FACTORY</title><style>
body { background: #071024; color: #e6f3f5; font-family: sans-serif; padding: 20px; }
.card { background: #0b1530; padding: 20px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px; }
button { background: #00b4a6; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; }
pre { background: #02131a; padding: 10px; height: 300px; overflow: auto; border-radius: 5px; color: #00ffcc; border: 1px solid #111; }
</style></head><body>
<h1>MDL Autonomous Factory v2.2.1</h1>
<div class="card"><h3>Upload Specification</h3><input type="file" id="f" multiple><input type="text" id="t" placeholder="Build Title"><button onclick="run()">BUILD SYSTEM</button></div>
<div class="card" id="bl"></div><div class="card"><pre id="lp">System Idle...</pre></div>
<script>
async function run() {
    const fd = new FormData();
    for(let file of document.getElementById('f').files) fd.append('files', file);
    fd.append('title', document.getElementById('t').value);
    const r = await fetch('/upload-spec', {method:'POST', body:fd});
    const d = await r.json(); track(d.build_id);
}
function track(id) {
    const es = new EventSource(`/builds/${id}/events`);
    document.getElementById('lp').innerText = `Tracking Build: ${id}\n`;
    es.onmessage = (e) => {
        const data = JSON.parse(e.data);
        document.getElementById('lp').innerText += `> ${data.msg}\n`;
        document.getElementById('lp').scrollTop = document.getElementById('lp').scrollHeight;
    };
}
async function lb() {
    const r = await fetch('/builds'); const d = await r.json();
    document.getElementById('bl').innerHTML = d.map(b => `<p>${b.title} [${b.status}] <button onclick="track('${b.id}')">TRACK</button></p>`).join('');
}
setInterval(lb, 5000); lb();
</script></body></html>"""
with open(FRONTEND_DIR / "upload_dashboard.html", "w") as f: f.write(HTML)

# 4. SERVER ENDPOINTS
app = FastAPI()
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def home(): return FileResponse(FRONTEND_DIR / "upload_dashboard.html")

@app.get("/builds")
def list_builds():
    cur = conn.execute("SELECT id, title, status FROM builds ORDER BY created_at DESC")
    return [{"id": r[0], "title": r[1], "status": r[2]} for r in cur.fetchall()]

@app.post("/upload-spec")
async def upload(background: BackgroundTasks, files: List[UploadFile] = File(...), title: str = Form(...)):
    bid = str(uuid.uuid4()); (SPECS_DIR/bid).mkdir()
    for f in files:
        async with aiofiles.open(SPECS_DIR/bid/f.filename, "wb") as out: await out.write(await f.read())
    conn.execute("INSERT INTO builds VALUES (?, ?, ?, ?, ?)", (bid, title, "QUEUED", "[]", time.time())); conn.commit()
    background.add_task(pipeline, bid); return {"build_id": bid}

async def pipeline(bid):
    for s in ["P0: Init", "P1: Spec Analysis", "P6: Validation", "P9: Provisioning", "P11: Render Deploy", "P13: Verified"]:
        await asyncio.sleep(2)
        cur = conn.execute("SELECT logs FROM builds WHERE id=?", (bid,))
        logs = json.loads(cur.fetchone()[0]); logs.append({"msg": s})
        conn.execute("UPDATE builds SET status=?, logs=? WHERE id=?", (s, json.dumps(logs), bid)); conn.commit()

@app.get("/builds/{bid}/events")
async def events(bid: str):
    async def stream():
        idx = 0
        while True:
            cur = conn.execute("SELECT logs, status FROM builds WHERE id=?", (bid,))
            row = cur.fetchone()
            if not row: break
            logs = json.loads(row[0])
            while idx < len(logs): yield f"data: {json.dumps(logs[idx])}\n\n"; idx += 1
            if "Verified" in row[1]: break
            await asyncio.sleep(1)
    return StreamingResponse(stream(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
