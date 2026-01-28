import requests
import datetime
from decimal import Decimal
from models.entities import Cotizacion, Moneda
from utils.logger import app_logger
from utils.decorators import safe_transaction

class BnaService:
    # Using ArgentinaDatos API - Free, open, historical
    API_URL = "https://api.argentinadatos.com/v1/cotizaciones/dolares/oficial"

    @classmethod
    def check_connectivity(cls):
        try:
            requests.get("https://www.google.com", timeout=3)
            return True
        except:
            return False

    @classmethod
    def fetch_history(cls):
        """
        Fetches full history of official dollar.
        Returns: list of dicts {fecha: date, compra: float, venta: float}
        """
        try:
            response = requests.get(cls.API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Format: [{"casa": "oficial", "compra": 10, "venta": 12, "fecha": "2011-01-03"}, ...]
            results = []
            for item in data:
                try:
                    d_str = item.get('fecha')
                    val_c = item.get('compra', 0.0)
                    val_v = item.get('venta', 0.0)
                    
                    dt = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
                    results.append({
                        "fecha": dt,
                        "compra": float(val_c),
                        "venta": float(val_v)
                    })
                except:
                    continue
            
            # Sort recent first
            results.sort(key=lambda x: x['fecha'], reverse=True)
            return results
        except Exception as e:
            app_logger.error(f"BNA API Error: {e}")
            return None

    @classmethod
    @safe_transaction
    def sync_rates(cls, session=None):
        """
        Syncs local DB with Official BNA rates (Authoritative).
        Updates existing records and inserts new ones.
        """
        if not cls.check_connectivity():
            return False, 0
            
        history = cls.fetch_history()
        if not history:
            return False, 0
            
        count_updates = 0
        
        # Optimization: Fetch all USD quotes to memory to avoid N queries
        # Map: date -> Cotizacion or dict
        existing_map = {
            row.fecha: row 
            for row in session.query(Cotizacion).filter(Cotizacion.moneda == Moneda.USD).all()
        }
        
        for item in history:
            target_date = item['fecha']
            new_compra = item['compra']
            new_venta = item['venta']
            
            if target_date in existing_map:
                # Update if different
                existing = existing_map[target_date]
                # Compare with small tolerance for floats
                # Convert DB Decimal to float for comparison
                # Compare with small tolerance for floats
                # Convert DB Decimal to float for comparison
                # if abs(float(existing.compra) - new_compra) > 0.001 or abs(float(existing.venta) - new_venta) > 0.001:
                if abs(float(existing.venta) - new_venta) > 0.001 or abs(float(existing.compra or 0) - new_compra) > 0.001:
                    existing.compra = new_compra
                    existing.venta = new_venta
                    count_updates += 1
            else:
                # Insert
                new_cot = Cotizacion(
                    fecha=target_date,
                    moneda=Moneda.USD,
                    compra=new_compra,
                    venta=new_venta
                )
                session.add(new_cot)
                count_updates += 1
        
        if count_updates > 0:
            app_logger.info(f"BNA Sync: {count_updates} rates synced (Official).")
            
        return True, count_updates
