import urllib.request
import json

try:
    print("Testing /vencimientos...")
    with urllib.request.urlopen("http://localhost:8000/vencimientos") as response:
        print(f"Status: {response.getcode()}")
        headers = response.info()
        print(f"Content-Type: {headers.get_content_type()}")
        body = response.read().decode('utf-8')
        if headers.get_content_type() == 'application/json':
            data = json.loads(body)
            print(f"JSON Items: {len(data)}")
        else:
            print(f"BODY START: {body[:200]}")
except Exception as e:
    print(f"ERROR: {e}")
