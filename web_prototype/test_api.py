
import requests
import json

try:
    print("Fetching dashboard stats from http://localhost:8000...")
    res = requests.get("http://localhost:8000/dashboard-stats")
    if res.status_code == 200:
        data = res.json()
        cats = data.get("distribucion_categorias", [])
        print(f"Status: 200 OK")
        print(f"Categories Data ({len(cats)} items): {json.dumps(cats, indent=2)}")
        print(f"Total Deuda: {data.get('total_deuda')}")
    else:
        print(f"Error: {res.status_code}")
        print(res.text)
except Exception as e:
    print(f"Connection Failed: {e}")
