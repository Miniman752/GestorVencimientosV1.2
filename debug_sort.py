import requests
import json

API_URL = "https://apis.datos.gob.ar/series/api/series"
SERIES_ID = "101.1_I2NG_2016_M_22"

def test_sort():
    print("Testing Sort Order...")
    # Try getting latest by sorting descending
    params = {
        "ids": SERIES_ID,
        "limit": 5,
        "format": "json",
    }
    # Usually sort param is "sort"
    # Try "time_index:desc" or "date:desc"
    # Based on docs (Andino): sort=<field> <direction>
    
    # Attempt 1: Default (We know this gives old data 2016/2021)
    
    print("-" * 20)
    print("Attempting 'last=5' (Pagination)")
    # Default behavior might return oldest, but maybe 'last' works?
    # Or start_date?
    # Actually, if I can't sort, I have to fetch ALL? (There are ~100 records since 2016)
    # limit=500?
    
    params = {
        "ids": SERIES_ID,
        "limit": 500, # Get EVERYTHING
        "format": "json",
    }
    
    try:
        resp = requests.get(API_URL, params=params, timeout=10)
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            count = len(data["data"])
            print(f"Total Records: {count}")
            print(f"Last Record (End of List): {data['data'][-1]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sort()
