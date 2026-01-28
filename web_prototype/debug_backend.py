import requests
try:
    print("Testing connection to http://localhost:8000...")
    resp = requests.get("http://localhost:8000", timeout=2)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"FAILED: {e}")
