import csv
import pandas as pd
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from models.entities import Cotizacion, Moneda
from utils.decorators import safe_transaction
from utils.logger import app_logger
from utils.format_helper import parse_fuzzy_date, parse_localized_float

class ForexService:

    @safe_transaction
    def import_from_dataframe(self, df, mapping_dict, session=None):
        """
        Imports data from a DataFrame based on mapping.
        Returns: (success_count, list_of_errors)
        """
        success_count = 0
        errors = []
        # from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        from models.entities import Cotizacion, Moneda
        # We need to ensure we have access to these. Assuming imports at file top or local.
        # But wait, imports are stripped in the view tool. 
        # I must ensure they are available. `Moneda` and `Cotizacion` are in `models.entities`.
        
        for index, row in df.iterrows():
            try:
                # 1. Parse Date
                col_fecha = mapping_dict.get('fecha')
                raw_date = row[col_fecha]
                date_val = parse_fuzzy_date(raw_date)
                
                if not date_val: continue

                # 2. Parse Values
                col_compra = mapping_dict.get('compra')
                col_venta = mapping_dict.get('venta')
                
                # Use robust helper
                val_compra = parse_localized_float(row[col_compra]) if col_compra in row else 0.0
                val_venta = parse_localized_float(row[col_venta]) if col_venta in row else 0.0
                
                # 3. Currency
                currency_str = mapping_dict.get('moneda_fixed', 'USD')
                moneda_enum = Moneda[currency_str]

                # 4. Upsert (Generic)
                existing = session.query(Cotizacion).filter_by(fecha=date_val, moneda=moneda_enum).first()
                if existing:
                     existing.venta = val_venta
                else:
                     new_cot = Cotizacion(fecha=date_val, moneda=moneda_enum, venta=val_venta)
                     session.add(new_cot)
                
                # session.execute(stmt) # Removed
                success_count += 1
            except Exception as row_e:
                 errors.append(f"Row {index}: {str(row_e)}")
        
        return success_count, errors


    @safe_transaction
    def import_bna_csv(self, filepath: str, session: Session = None):
        count = 0
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            # Expected format: Fecha;Moneda;Compra;Venta
            # Example: 15/01/2024;USD;800,50;820,00
            for row in reader:
                try:
                    if len(row) < 4: continue
                    date_str, currency_str, buy_str, sell_str = row
                    
                    # Parse Date
                    fecha = parse_fuzzy_date(date_str)
                    if not fecha: continue

                    # Parse Currency
                    moneda = Moneda.USD if "USD" in currency_str.upper() else None
                    if not moneda: continue # Only USD for now

                    # Parse Floats (European format 1.000,00 support)
                    compra = parse_localized_float(buy_str)
                    venta = parse_localized_float(sell_str)

                    # Upsert
                    cot = session.query(Cotizacion).filter_by(fecha=fecha, moneda=moneda).first()
                    if not cot:
                        cot = Cotizacion(fecha=fecha, moneda=moneda, venta=venta)
                        session.add(cot)
                    else:
                        # cot.compra = compra
                        cot.venta = venta
                    count += 1
                except Exception as e:
                    app_logger.error(f"Error importing row {row}: {e}")
        return count

    def get_rate(self, target_date: date, session: Session, max_lookback_days: int = 60) -> float:
        """Returns SELL rate (Venta) closest to target_date (past or present)."""
        # Improved logic: Query Last <= target_date
        # We search specifically for the most recent quote available on or before the target.
        cot = session.query(Cotizacion).filter(
            Cotizacion.fecha <= target_date,
            Cotizacion.moneda == Moneda.USD
        ).order_by(Cotizacion.fecha.desc()).first()
        
        if cot:
             return float(cot.venta)
        
        # Fallback: Try to find ANY rate? Or return 1.0
        # If no rate exists in simple past, maybe it's a future date and we have no history?
        # Try finding the latest available rate overall if the above failed (e.g. target date is way before first load)
        # But logically for 'conversion' of future debts, we want the LATEST loaded rate.
        
        latest = session.query(Cotizacion).filter(Cotizacion.moneda == Moneda.USD).order_by(Cotizacion.fecha.desc()).first()
        if latest:
            return float(latest.venta)

        return 1.0 # True Fallback if table empty

    def convert(self, amount: float, from_curr: Moneda, to_curr: str, rate_date: date, session: Session):
        if from_curr.value == to_curr:
            return amount
        
        rate = self.get_rate(rate_date, session)
        if rate == 0: return amount # Avoid div zero

        # Ensure compatibility
        from decimal import Decimal
        if isinstance(amount, Decimal):
            # Convert rate (float) to Decimal for precision
            rate = Decimal(str(rate))
        else:
            # If amount is float, ensure rate is float
            rate = float(rate)

        # Normalize target currency to string for comparison
        to_curr_str = to_curr.value if isinstance(to_curr, Moneda) else str(to_curr)

        if from_curr == Moneda.USD and to_curr_str == Moneda.ARS.value:
            return amount * rate
        elif from_curr == Moneda.ARS and to_curr_str == Moneda.USD.value:
            return amount / rate
        
        return amount

    @safe_transaction
    def update_cotizacion(self, date_obj, currency_str: str, buy: float, sell: float, audit_service=None, session: Session = None):
        """Updates or inserts a single cotizacion."""
        # Upsert logic moved from Controller
        moneda_enum = Moneda[currency_str]
        
        existing = session.query(Cotizacion).filter(
            Cotizacion.fecha == date_obj, 
            Cotizacion.moneda == moneda_enum
        ).first()

        if existing:
            old_val = f"V:{existing.venta}"
            # existing.compra = buy
            existing.venta = sell
            
            if audit_service:
                audit_service.log(
                    module="Forex", action="UPDATE", entity_id=f"{date_obj}|{currency_str}",
                    old_value=old_val, new_value=f"V:{sell}", details="Actualización Manual"
                )
        else:
            new_cot = Cotizacion(fecha=date_obj, moneda=moneda_enum, venta=sell)
            session.add(new_cot)
            if audit_service:
                audit_service.log(
                    module="Forex", action="CREATE", entity_id=f"{date_obj}|{currency_str}",
                    new_value=f"V:{sell}", details="Creación Manual"
                )
        return True

    @safe_transaction
    def delete_cotizacion(self, date_obj, currency_str: str, audit_service=None, session: Session = None):
        """Deletes a cotizacion."""
        moneda_enum = Moneda[currency_str]
        row = session.query(Cotizacion).filter(
            Cotizacion.fecha == date_obj, 
            Cotizacion.moneda == moneda_enum
        ).first()
        
        if row:
            old_val = f"V:{row.venta}"
            session.delete(row)
            if audit_service:
                audit_service.log(
                    module="Forex", action="DELETE", entity_id=f"{date_obj}|{currency_str}",
                    old_value=old_val, details="Eliminación Manual"
                )
            return True
        return False


