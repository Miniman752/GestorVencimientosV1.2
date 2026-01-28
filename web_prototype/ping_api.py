import requests
import time

try:
    print("Pinging API Root...")
    start = time.time()
    res = requests.get("http://localhost:8000/", timeout=5)
    print(f"Root: {res.status_code} in {time.time() - start:.2f}s")
    
    print("Pinging Vencimientos...")
    start = time.time()
    print(f"Vencimientos: {res.status_code}")
    print(f"RAW BODY: {res.text[:1000]}") 
    print(f"Items: {len(res.json())}")
except Exception as e:
    print(f"ERROR: {e}")
