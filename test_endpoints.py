import requests
import json
import os

BASE_URL = "http://127.0.0.1:8000"

def test_flow():
    print("1. Testing GET /documents ...")
    r = requests.get(f"{BASE_URL}/documents")
    print("Current documents:", r.json())
    
    print("\n2. Testing POST /upload with acme_report.pdf ...")
    file_path = "acme_report.pdf"
    if not os.path.exists(file_path):
        print("acme_report.pdf not found in root directory!")
        return
        
    with open(file_path, "rb") as f:
        files = {"files": (file_path, f, "application/pdf")}
        r = requests.post(f"{BASE_URL}/upload", files=files)
        print("Upload response:", r.json())
        
    print("\n3. Testing POST /extract-insights for acme_report.pdf ...")
    payload = {"filename": "acme_report.pdf"}
    r = requests.post(f"{BASE_URL}/extract-insights", json=payload)
    print("Insights response:", json.dumps(r.json(), indent=2))
    
    print("\n4. Testing POST /compare-papers ...")
    payload = {"filenames": ["acme_report.pdf"]}
    r = requests.post(f"{BASE_URL}/compare-papers", json=payload)
    print("Comparison response preview:")
    res_data = r.json()
    print("Markdown table & summary preview:\n", res_data.get("comparison_markdown", "No markdown returned")[:500])
    
    print("\n5. Testing POST /set-model (SciBERT) ...")
    payload = {"model_name": "SciBERT"}
    r = requests.post(f"{BASE_URL}/set-model", json=payload)
    print("Set model SciBERT response:", r.json())
    
    print("\n6. Testing POST /set-model (MiniLM) ...")
    payload = {"model_name": "MiniLM"}
    r = requests.post(f"{BASE_URL}/set-model", json=payload)
    print("Set model MiniLM response:", r.json())

if __name__ == "__main__":
    test_flow()
