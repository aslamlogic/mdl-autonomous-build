from engine.llm_interface import generate
from datetime import datetime

class IterationController:
    def __init__(self):
        self.allowed_files = ["main.py", "api.py", "requirements.txt"]

    def _allowed_files(self):
        return self.allowed_files

    def run(self, spec_text: str):
        print(f"[{datetime.now()}] Starting build with spec length: {len(spec_text)}")
        try:
            result = generate(spec_text, None, self._allowed_files())
        except Exception as e:
            result = {"status": "error", "error": str(e)}
        print(f"[{datetime.now()}] Build completed with status: {result.get('status', 'unknown')}")
        return result

# single exported controller instance used by meta_ui/api.py
controller = IterationController()
