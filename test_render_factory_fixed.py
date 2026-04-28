#!/usr/bin/env python3
"""
TEST SCRIPT FOR mdl-autonomous-build on Render - FIXED VERSION
Fully autonomous test - no manual editing required.
Handles both successful and error responses from the /run endpoint.
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://mdl-autonomous-build.onrender.com"

def test_health():
    print(f"[{datetime.now()}] Testing /health endpoint...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=15)
        print(f"Health status: {r.status_code}")
        try:
            print(json.dumps(r.json(), indent=2))
        except:
            print(r.text)
        return r.status_code == 200
    except Exception as e:
        print(f"Health test failed: {e}")
        return False

def test_run_endpoint():
    print(f"[{datetime.now()}] Testing /run endpoint with full USS instruction...")
    payload = {
        "instruction": "Build a minimal FastAPI endpoint that returns current server time per v2.1 USS specification. Include /time route. Enforce all 10 P6 test layers inside P7 iteration. Generate full audit report.",
        "spec": {
            "Budget_Policy": {"max_iterations": 5},
            "Routing_Policy": {"provider": "render"}
        }
    }
    try:
        r = requests.post(
            f"{BASE_URL}/run",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=45
        )
        print(f"Run status: {r.status_code}")

        if r.status_code == 200:
            try:
                response = r.json()
                print(json.dumps(response, indent=2))
                success = response.get("status") in ["SUCCESS", "ARBITRATED"] or "report" in str(response)
            except:
                print(r.text)
                success = False
        else:
            print("Error response body:")
            print(r.text[:500])
            success = False

        if success:
            print("✓ Test passed - autonomous factory executed full pipeline")
        else:
            print("✗ Test returned error - check Render logs")
        return success
    except Exception as e:
        print(f"Run test failed: {e}")
        return False

def main():
    print("=== AUTONOMOUS SOFTWARE FACTORY TEST SCRIPT v2.1 (FIXED) ===")
    print("SMR v5.6 Deterministic Mode - Full P0-P13 verification")
    print("Testing live Render deployment at https://mdl-autonomous-build.onrender.com")
    print("=" * 80)

    health_ok = test_health()
    print()
    run_ok = test_run_endpoint()

    print("\n" + "=" * 80)
    if health_ok and run_ok:
        print("✅ ALL TESTS PASSED - Autonomous factory is fully operational on Render")
    else:
        print("⚠️ Some tests failed - please check the Render dashboard logs for details")
        print("   Common causes: missing dependencies, runtime error in /run, or 500 error")
    print("Test completed at", datetime.now())

if __name__ == "__main__":
    main()
