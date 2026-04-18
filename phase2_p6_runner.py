from fastapi.testclient import TestClient
from meta_ui.api import app

print("P6 VALIDATION START")

client = TestClient(app)
r = client.get("/health")

assert r.status_code == 200, f"Status not 200: {r.status_code}"
assert isinstance(r.json(), dict), "Response not JSON"
assert "status" in r.json(), "Missing 'status' key"

print("P6_PASS", r.json())
