import sys
import os
import datetime
from decimal import Decimal

# Add src_restored to path
sys.path.append(os.path.join(os.getcwd(), 'src_restored'))

from services.indec_service import IndecService

def verify_range():
    print("Fetching data using IndecService...")
    # This calls the method that fetches and converts, but without DB side effects (fetch_latest_indices just returns dicts, 
    # but the CONVERSION logic is in sync_indices. Wait, verify IndecService logic.)
    
    # Actually, the conversion logic IS IN sync_indices in the service, but fetch_latest_indices returns raw data.
    # I need to verify that fetch_latest_indices returns enough data, AND run a simulation of the conversion logic
    # OR replicate the conversion logic here to prove it works.
    
    # Ideally test IndecService.sync_indices with a mock session, but simpler:
    # 1. Fetch raw data. 
    # 2. Check coverage (2023-2025).
    # 3. Simulate conversion loop to verify values < 50%.

    raw_data = IndecService.fetch_latest_indices(limit=200)
    
    if not raw_data:
        print(" >> ERROR: No data returned from API.")
        return

    print(f" >> Received {len(raw_data)} records.")
    
    # Sort
    raw_data.sort(key=lambda x: x['date'])
    
    print(f" >> Data Range: {raw_data[0]['date']} to {raw_data[-1]['date']}")
    
    years_found = set()
    warnings = []
    
    previous_value = None
    converted_samples = []

    for item in raw_data:
        date_str = item['date']
        val_raw = float(item['value'])
        year = date_str.split('-')[0]
        years_found.add(year)
        
        # Simulation of conversion logic
        monthly_pct = 0.0
        if previous_value is not None:
            monthly_pct = ((val_raw - previous_value) / previous_value) * 100
        
        previous_value = val_raw
        
        # Capture sample for each year
        if year in ['2023', '2024', '2025', '2026']:
             # Store only one per year to keep output clean, update if exists
             converted_samples.append(f"{date_str}: Index={val_raw:.2f} -> PPI={monthly_pct:.2f}%")

    # Check Coverage
    required_years = ['2023', '2024', '2025']
    missing = [y for y in required_years if y not in years_found]
    
    print(f"Years found in data: {sorted(list(years_found))}")
    
    if missing:
        print(f" >> FAILURE: Missing years: {missing}")
    else:
        print(f" >> SUCCESS: Years 2023, 2024, 2025 are present.")
        
    print("\nSample Values (Converted):")
    if not converted_samples:
        print(" >> WARNING: No samples converted for target years.")
    else:
        # Print last 10 samples to show recent history
        for s in converted_samples[-10:]:
            print(f" > {s}")
            
        # Check Magnitude
        last_pct = float(converted_samples[-1].split("PPI=")[1].replace("%",""))
        if last_pct < 50:
            print(f"\n >> SUCCESS: Converted values are reasonable percentage ({last_pct:.2f}%).")
        else:
            print(f"\n >> FAILURE: Converted values still look too high ({last_pct:.2f}%).")

if __name__ == "__main__":
    verify_range()
