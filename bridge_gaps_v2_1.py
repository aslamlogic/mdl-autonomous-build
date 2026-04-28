import os, re
from pathlib import Path

def bridge():
    root = Path.cwd()
    print(f"SMR v5.6: Bridging gaps in {root}")
    
    # 1. Fix render.yaml (remove destructive echo lines)
    r_yaml = root / "render.yaml"
    if r_yaml.exists():
        content = r_yaml.read_text()
        new_content = re.sub(r'buildCommand:.*pip install -r requirements\.txt', 
                            'buildCommand: |\n      pip install -r requirements.txt', 
                            content, flags=re.DOTALL)
        r_yaml.write_text(new_content)
        print("- Fixed render.yaml")

    # 2. Fix requirements.txt (force correct versions)
    reqs = "fastapi==0.115.0\nuvicorn==0.30.6\nopenai==1.35.0\npydantic==2.8.2\n"
    (root / "requirements.txt").write_text(reqs)
    print("- Fixed requirements.txt")

    # 3. Fix engine/llm_interface.py (correct OpenAI calling standard)
    llm_p = root / "engine" / "llm_interface.py"
    llm_p.parent.mkdir(parents=True, exist_ok=True)
    llm_p.write_text('import os\nfrom openai import OpenAI\ndef generate(prompt, **kwargs):\n    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))\n    res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])\n    return {"status":"success", "content": res.choices[0].message.content}')
    print("- Fixed engine/llm_interface.py")

    # 4. Fix meta_ui/api.py (restore reliable /run)
    api_p = root / "meta_ui" / "api.py"
    api_p.write_text('from fastapi import FastAPI\nfrom iteration.controller import controller\nfrom pydantic import BaseModel\napp = FastAPI()\nclass BuildRequest(BaseModel):\n    instruction: str\n@app.get("/health")\ndef h(): return {"status":"ok"}\n@app.post("/run")\ndef r(req: BuildRequest): return controller.run(req.instruction)')
    print("- Fixed meta_ui/api.py")

    print("\nBRIDGE COMPLETE. Run these commands now:")
    print("python bridge_gaps_v2_1.py && git add . && git commit -m 'SMR v5.6 fix' && git push")

if __name__ == "__main__":
    bridge()
