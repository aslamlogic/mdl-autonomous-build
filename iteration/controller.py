from engine.llm_interface import generate
from datetime import datetime

class BuildController:
    def __init__(self):
        self.allowed_files = ["main.py", "api.py", "requirements.txt"]

    def _allowed_files(self):
        return self.allowed_files

    def run(self, spec_text: str):
        print(f"[{datetime.now()}] Starting build with spec length: {len(spec_text)}")
        result = generate(spec_text, None, self._allowed_files())
        print(f"[{datetime.now()}] Build completed with status: {result.get('status', 'unknown')}")
        return result

controller = BuildController()
