
from datetime import timedelta, date
from sqlalchemy.orm import Session
from database import SessionLocal
from models.entities import Cotizacion, Moneda
from utils.logger import app_logger

class CurrencyService:
    def __init__(self):
        self._cache = {} # Key: (date, currency), Value: rate

    def get_historical_rate(self, target_date: date, currency_str: str = "USD", max_recursion=7):
        """
        Finds the selling rate for a given date.
        If not found, recursively checks previous days up to max_recursion.
        Returns None if not found after recursion.
        """
        if isinstance(target_date, str):
            # Handle string dates just in case
            try:
                target_date = date.fromisoformat(target_date)
            except:
                pass

        cache_key = (target_date, currency_str)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Base case for recursion
        if max_recursion < 0:
            return None

        db = SessionLocal()
        try:
            money_enum = Moneda[currency_str]
            rate = db.query(Cotizacion).filter(
                Cotizacion.fecha == target_date,
                Cotizacion.moneda == money_enum
            ).first()

            if rate:
                val = rate.venta
                self._cache[cache_key] = val
                return val
            else:
                # Recursive Step: Try yesterday
                # We don't cache failures for the specific date if we found a fallback, 
                # but conceptually the "Effective Rate" for Sunday IS Friday's rate.
                # So we COULD cache Friday's rate as Sunday's rate to save recursion next time.
                
                prev_day = target_date - timedelta(days=1)
                fallback_val = self.get_historical_rate(prev_day, currency_str, max_recursion - 1)
                
                if fallback_val:
                    # Cache this date as using the fallback value to speed up future lookups
                    self._cache[cache_key] = fallback_val
                    return fallback_val
                return None

        except Exception as e:
            app_logger.error(f"Error getting rate for {target_date}: {e}")
            return None
        finally:
            db.close()

    def convert_to_usd(self, amount_ars, target_date):
        """Helper to convert ARS to USD using smart historical lookup."""
        if not amount_ars: return 0.0
        
        rate = self.get_historical_rate(target_date, "USD")
        if rate and rate > 0:
            return amount_ars / rate
        return 0.0 # Or raise error / return None? 0.0 is safer for UI sums


