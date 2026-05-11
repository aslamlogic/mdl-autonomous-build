# DARL - Dynamic Authority & Registry Layer (SST v2.2 §7)
import json
import os

class Registry:
    def __init__(self):
        self.state_file = "registry_state.json"
        self.authorized_state = self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {"version": "2.2", "status": "initialized", "debt": 0}

    def verify_authority(self, spec_version):
        # Truth Discipline (§1.1): Ensure no version debt
        if spec_version != self.authorized_state["version"]:
            raise Exception(f"Version Debt Detected: {spec_version} != Canonical 2.2")
        return True

registry = Registry()
