import requests
import os

# CONFIGURATION
SERVICE_URL = "https://mdl-autonomous-build.onrender.com"
# Updated to match your screenshot filename exactly
SST_PATH = "Formal Technical specification for Autonomous SW factory v 2.1.pdf"
INSTRUCTION = "Apply Formal Technical specification v2.1 to reconcile the architecture, enforce P0-P13 standards, and perform a full iteration."

def run():
    if not os.path.exists(SST_PATH):
        print(f"ERROR: File not found: {SST_PATH}")
        print("Please drag and drop the PDF into your Codespace Explorer panel first.")
        return

    print(f">>> [P11] UPLOADING SPECIFICATION: {SST_PATH}...")
    try:
        with open(SST_PATH, "rb") as f:
            up = requests.post(f"{SERVICE_URL}/upload-spec", files={"file": f})
        
        if up.status_code in [200, 201]:
            print(f">>> Success: Spec uploaded to repository.")
            
            print(">>> [P7] TRIGGERING AUTONOMOUS BUILD PIPELINE...")
            run_req = requests.post(f"{SERVICE_URL}/run", json={"instruction": INSTRUCTION})
            print(f">>> Request Status: {run_req.status_code} - {run_req.json().get('status')}")
            print(">>> The factory is now running in the background on Render.")
        else:
            print(f">>> Failed to upload spec. Status: {up.status_code} - {up.text}")
            
    except Exception as e:
        print(f"CONNECTION ERROR: {str(e)}")

if __name__ == "__main__":
    run()
