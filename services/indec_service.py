
import requests
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from models.entities import IndiceEconomico
from utils.logger import app_logger
from decimal import Decimal
from utils.decorators import safe_transaction

class IndecService:
    API_URL = "https://apis.datos.gob.ar/series/api/series"
    SERIES_ID = "101.1_I2NG_2016_M_22" # IPC Nivel General Base 2016 (Active)

    @classmethod
    def check_connectivity(cls):
        """Simple check to see if we can reach Google (or the API itself)."""
        try:
            requests.get("https://www.google.com", timeout=3)
            return True
        except:
            return False

    @classmethod
    def fetch_latest_indices(cls, limit=200): # Increased to 200 to cover full history (2016-Now is ~116 records)
        """
        Fetches the last N months of IPC data.
        Returns a list of dicts: [{'date': '2023-10-01', 'value': 1234.56}, ...]
        """
        try:
            params = {
                "ids": cls.SERIES_ID,
                "limit": limit,
                "format": "json"
            }
            # Add trailing slash just in case, or default to standard
            response = requests.get(cls.API_URL, params=params, timeout=5)
            
            if response.status_code == 400:
                app_logger.info(f"INDEC Sync: API endpoint returned 400 (Series ID likely changed/deprecated). Skipping sync.")
                return None
                
            response.raise_for_status()
            
            data = response.json()
            # Parse response
            # Format usually: {"data": [["2023-10-01", 123.45], ...], ...}
            
            results = []
            if "data" in data:
                for row in data["data"]:
                    date_str = row[0] # "2023-10-01"
                    val = row[1]
                    results.append({
                        "date": date_str,
                        "value": val
                    })
            return results
        except Exception as e:
            app_logger.error(f"INDEC API Error: {e}")
            return None

    @classmethod
    @safe_transaction
    def sync_indices(cls, session=None):
        """
        Syncs local DB with API data.
        Returns: (success_bool, count_new_records_int)
        """
        if not cls.check_connectivity():
            return False, 0

        api_data = cls.fetch_latest_indices()
        if not api_data:
            return False, 0

        count_new = 0
        
        try:
            # Sort chronologically to calculate variations
            api_data.sort(key=lambda x: x['date'])
            
            previous_value = None
            
            for item in api_data:
                fecha_dt = datetime.datetime.strptime(item["date"], "%Y-%m-%d").date()
                current_index_value = Decimal(str(item["value"])) # This is the Index (e.g. 5000)
                
                # Calculate monthly variation %
                # Logic: (Current - Previous) / Previous * 100
                monthly_pct = Decimal(0)
                
                if previous_value is not None and previous_value > 0:
                    monthly_pct = ((current_index_value - previous_value) / previous_value) * 100
                    
                previous_value = current_index_value
                
                # Skip the very first record as we can't calculate its variation
                if monthly_pct == 0 and previous_value == current_index_value and len(api_data) > 1 and item == api_data[0]:
                     continue

                # Check if exists
                exists = session.query(IndiceEconomico).filter_by(periodo=fecha_dt).first()
                
                if not exists:
                    # Create new record with Percentage Value
                    new_idx = IndiceEconomico(
                        periodo=fecha_dt,
                        valor=monthly_pct
                        # descripcion removed (not in model)
                    )
                    session.add(new_idx)
                    count_new += 1
                else:
                    # Optional: Update existing if it looks like an Index (>100) to fix bad data
                    if exists.valor > 50: # Standard inflation rarely exceeds 50% monthly... yet.
                        exists.valor = monthly_pct
                        # exists.descripcion removed
                        count_new += 1 # Count as 'fixed'
            
            if count_new > 0:
                # session.commit() // Safe transaction handles commit
                app_logger.info(f"INDEC Sync: {count_new} records added/fixed (Converted Index to %).")
            return True, count_new
            
        except Exception as e:
            app_logger.error(f"INDEC Sync DB Error: {e}")
            raise e


