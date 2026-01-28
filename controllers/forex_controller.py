
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from database import get_db, SessionLocal
from models.entities import Cotizacion, Moneda
from utils.logger import app_logger
from services.audit_service import AuditService
from services.forex_service import ForexService
from utils.import_helper import load_data_file
from utils.format_helper import parse_fuzzy_date, parse_localized_float
from datetime import date, datetime

class ForexController:
    def __init__(self):
        self.audit = AuditService()

    def sync_bna(self):
        """Triggers manual BNA sync."""
        from services.bna_service import BnaService
        db = SessionLocal()
        try:
            success, count = BnaService.sync_rates(session=db)
            if success:
                if count > 0:
                     return True, f"Sincronización Exitosa: {count} cotizaciones actualizadas."
                else:
                     return True, "Sincronización Exitosa: No hubo cambios (estaba al día)."
            else:
                 return False, "Error de conexión o fallo en la API."
        except Exception as e:
            app_logger.error(f"Sync error: {e}")
            return False, str(e)
        finally:
            db.close()
    def get_cotizaciones(self, year=None, month=None):
        """Fetches cotizaciones, optionally filtered by year and month."""
        db = SessionLocal()
        try:
            query = db.query(Cotizacion)
            
            if year:
                from calendar import monthrange
                from datetime import date
                
                # Determine range
                start_month = month if month else 1
                end_month = month if month else 12
                
                # Start Date
                start_date = date(year, start_month, 1)
                
                # End Date
                last_day = monthrange(year, end_month)[1]
                end_date = date(year, end_month, last_day)
                
                query = query.filter(Cotizacion.fecha >= start_date, Cotizacion.fecha <= end_date)
            
            # Order by date desc
            query = query.order_by(Cotizacion.fecha.desc())
            return query.all()
        except Exception as e:
            app_logger.error(f"Error fetching cotizaciones: {e}")
            return []
        finally:
            db.close()

    def update_cotizacion_manual(self, date_obj, currency_str, buy, sell):
        """Updates or inserts a single cotizacion via Service."""
        try:
            # Delegate db logic to Service (transaction handled there)
            # We pass self.audit to let service log.
            # Ideally AuditService should be injected into ForexService, but for now we pass it.
            # We need to instantiate ForexService here or in __init__? 
            # It's not in __init__ yet.
            svc = ForexService() 
            svc.update_cotizacion(date_obj, currency_str, buy, sell, audit_service=self.audit)
            return True, "Cotización actualizada."
        except Exception as e:
            app_logger.error(f"Error updating cotizacion: {e}")
            return False, str(e)

    def delete_cotizacion(self, date_obj, currency_str):
        """Deletes a cotizacion via Service."""
        try:
            svc = ForexService()
            if svc.delete_cotizacion(date_obj, currency_str, audit_service=self.audit):
                return True, "Cotización eliminada."
            else:
                return False, "No se encontró el registro."
        except Exception as e:
            app_logger.error(f"Error deleting cotizacion: {e}")
            return False, str(e)



    def preview_csv(self, file_path):
        """Reads first rows for preview."""
        try:
            # For preview we might default to 0, or try to guess. 
            # Simple preview: load and head
            df = load_data_file(file_path, header_row=0) 
            return True, df.head(5)
        except Exception as e:
            return False, str(e)

    def _detect_delimiter(self, file_path):
        # Deprecated by import_helper, keeping for legacy safety if called elsewhere
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                header = f.readline()
                if ';' in header: return ';'
        except: pass
        return ','

    def process_import(self, file_path, mapping_dict):
        """
        Imports CSV data via Service.
        """
        try:
            df = load_data_file(file_path)
            # Delegate to Service
            svc = ForexService()
            success, errors = svc.import_from_dataframe(df, mapping_dict)
            
            return True, f"Imported {success} rows. Errors: {len(errors)}"

        except Exception as e:
            app_logger.error(f"Import failed: {e}")
            return False, str(e)
    def get_active_years(self):
        """Returns list of active years for combo box."""
        db = SessionLocal()
        try:
            from models.entities import YearConfig
            years = db.query(YearConfig.year).filter(YearConfig.is_active == 1).order_by(YearConfig.year.desc()).all()
            return [str(y[0]) for y in years]
        except Exception as e:
            app_logger.error(f"Error fetching active years: {e}")
            return ["2025"] # Fallback
        finally:
            db.close()

    def get_all_years_config(self):
        """Returns list of all configured years with status."""
        db = SessionLocal()
        try:
            from models.entities import YearConfig
            # If empty, maybe seed?
            years = db.query(YearConfig).order_by(YearConfig.year.desc()).all()
            if not years:
                # Seed current + prev + next
                # Prevent infinite recursion if add_year fails
                if self.add_year(2025) and self.add_year(2024):
                    return self.get_all_years_config()
                else:
                    return [] # Stop if seeding fails
            return years
        except Exception as e:
            app_logger.error(f"Error fetching config years: {e}")
            return []
        finally:
            db.close()

    def add_year(self, year: int):
        db = SessionLocal()
        try:
            from models.entities import YearConfig
            yg = db.query(YearConfig).get(year)
            if yg:
                yg.is_active = 1
            else:
                db.add(YearConfig(year=year, is_active=1))
            db.commit()
            return True
        except Exception as e:
            app_logger.error(f"Error adding year {year}: {e}")
            return False
        finally:
            db.close()

    def toggle_year_status(self, year: int, active: bool):
        db = SessionLocal()
        try:
            from models.entities import YearConfig
            yg = db.query(YearConfig).get(year)
            if yg:
                yg.is_active = 1 if active else 0
                db.commit()
        except Exception as e:
             app_logger.error(f"Error toggling year {year}: {e}")
        finally:
            db.close()

    def delete_year(self, year: int):
        """Deletes a year configuration."""
        db = SessionLocal()
        try:
            from models.entities import YearConfig
            yg = db.query(YearConfig).get(year)
            if yg:
                db.delete(yg)
                db.commit()
                return True, "Año eliminado correctamente."
            return False, "Año no encontrado."
        except Exception as e:
            app_logger.error(f"Error deleting year {year}: {e}")
            return False, str(e)
        finally:
            db.close()

    def update_year(self, old_year: int, new_year: int):
        """Renames a year configuration (Create New + Delete Old)."""
        db = SessionLocal()
        try:
            from models.entities import YearConfig
            
            # Check if new exists
            if db.query(YearConfig).get(new_year):
                return False, f"El año {new_year} ya existe."
            
            # Get old
            old_yg = db.query(YearConfig).get(old_year)
            if not old_yg:
                return False, "El año original no se encontró."
            
            # Create new with same properties
            new_yg = YearConfig(year=new_year, is_active=old_yg.is_active)
            db.add(new_yg)
            
            # Delete old
            db.delete(old_yg)
            
            db.commit()
            return True, "Año actualizado correctamente."
        except Exception as e:
            db.rollback()
            app_logger.error(f"Error updating year {old_year} -> {new_year}: {e}")
            return False, str(e)
        finally:
            db.close()

    def get_chart_data(self, currency_str=Moneda.USD.value, year=None, month=None, limit=None):
        """
        Returns DataFrame with technical indicators (MACD).
        Filters by Year/Month if provided, otherwise uses limit.
        """
        db = SessionLocal()
        try:
            moneda = Moneda[currency_str]
            query = db.query(Cotizacion).filter(Cotizacion.moneda == moneda)
            
            if year:
                from datetime import date
                from calendar import monthrange
                
                # Filter range
                start_month = month if month else 1
                end_month = month if month else 12
                
                start_date = date(int(year), start_month, 1)
                last_day = monthrange(int(year), end_month)[1]
                end_date = date(int(year), end_month, last_day)
                
                query = query.filter(Cotizacion.fecha >= start_date, Cotizacion.fecha <= end_date)
            
            # Sort for plotting (Time ascending)
            # If no filter and limit, take last N
            if not year and limit:
                 # Subquery optimization or just get all and slice? 
                 # Get desc limit then reverse
                 records = query.order_by(Cotizacion.fecha.desc()).limit(limit).all()
                 records.reverse() 
            else:
                 records = query.order_by(Cotizacion.fecha.asc()).all()
            
            if len(records) < 2: return None # Need at least 2 for lines
            
            data = [{"fecha": r.fecha, "venta": float(r.venta)} for r in records]
            
            # Convert to DF
            df = pd.DataFrame(data)
            df['fecha'] = pd.to_datetime(df['fecha'])
            
            # --- TRADING VIEW INDICATORS ---
            
            # 1. Pseudo-OHLC (Simulate Candles)
            # Open = Previous Close
            df['prev_close'] = df['venta'].shift(1)
            # Fill first with current (flat candle)
            df['prev_close'] = df['prev_close'].fillna(df['venta'])
            
            df['Open'] = df['prev_close']
            df['Close'] = df['venta']
            df['High'] = df[['Open', 'Close']].max(axis=1)
            df['Low'] = df[['Open', 'Close']].min(axis=1)
            
            # Color: Green if Close >= Open, else Red
            df['color'] = df.apply(lambda x: '#2ECC71' if x['Close'] >= x['Open'] else '#E74C3C', axis=1)

            # 2. Moving Averages (Ribbon)
            df['EMA_12'] = df['venta'].ewm(span=12, adjust=False).mean()
            df['EMA_26'] = df['venta'].ewm(span=26, adjust=False).mean()
            # SMA 20 (Standard Bollinger/Trend base)
            df['SMA_20'] = df['venta'].rolling(window=20).mean()
            
            # 3. MACD
            df['MACD'] = df['EMA_12'] - df['EMA_26']
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Hist'] = df['MACD'] - df['Signal']
            
            # 4. Signals (Crossovers)
            df['prev_MACD'] = df['MACD'].shift(1)
            df['prev_Signal'] = df['Signal'].shift(1)
            
            def get_signal(row):
                if pd.isna(row['prev_MACD']): return None
                if row['prev_MACD'] < row['prev_Signal'] and row['MACD'] > row['Signal']: return "BUY"
                if row['prev_MACD'] > row['prev_Signal'] and row['MACD'] < row['Signal']: return "SELL"
                return None

            df['Trade_Signal'] = df.apply(get_signal, axis=1)
            
            # --- 5. AI PROJECTION (Linear Trend) ---
            # Project 7 days into future based on last 20 days trend
            try:
                import numpy as np
                from datetime import timedelta
                LOOKBACK = 15
                PROJECT_DAYS = 7
                
                if len(df) > LOOKBACK:
                    # Get last N days
                    recent = df.tail(LOOKBACK).copy()
                    
                    # Create X (days from start) and Y (price)
                    # We use ordinal date for regression
                    recent['date_ord'] = recent['fecha'].map(lambda d: d.toordinal())
                    x = recent['date_ord'].values
                    y = recent['venta'].values
                    
                    # Linear Regression (Polyfit deg 1)
                    slope, intercept = np.polyfit(x, y, 1)
                    
                    # Generate Future Data
                    last_date = df['fecha'].iloc[-1]
                    future_rows = []
                    
                    for i in range(1, PROJECT_DAYS + 1):
                        next_date = last_date + timedelta(days=i)
                        pred_price = slope * next_date.toordinal() + intercept
                        
                        # Add some "noise" or dampening? No, straight line is clear "projection"
                        future_rows.append({
                            'fecha': next_date,
                            'venta': pred_price,
                            'type': 'projection'
                        })
                        
                    df_future = pd.DataFrame(future_rows)
                    # Combine. We won't have indicators for future, nor candles (unless we simulate)
                    # We just want a line.
                    return pd.concat([df, df_future], ignore_index=True)
            except Exception as e:
                print(f"Projection Error: {e}")
            
            return df
            
        except Exception as e:
            app_logger.error(f"Chart data error: {e}")
            return None
        finally:
            db.close()

    def get_strategic_analysis(self, currency_str=Moneda.USD.value):
        """Returns structured advice based on technicals"""
        try:
            df = self.get_chart_data(currency_str)
            if df is None or len(df) < 26:
                return None
                
            # Separate Real vs Projection
            # If no projection (e.g. error/short data), all is real
            if 'type' not in df.columns: df['type'] = 'real'
            
            is_proj = df['type'] == 'projection'
            df_real = df[~is_proj].copy()
            df_proj = df[is_proj].copy()
            
            if df_real.empty: return None
            
            last_real = df_real.iloc[-1]
            last_price = last_real['venta']
            
            # 1. Trend Analysis (EMA Ribbon) on REAL data
            # EMA_12 > EMA_26 = Bullish
            is_bullish = last_real['EMA_12'] > last_real['EMA_26']
            trend_str = "▲ ALCISTA" if is_bullish else "▼ BAJISTA"
            
            # 2. Strength (MACD) on REAL data
            last_hist = last_real['Hist']
            prev_hist = df_real.iloc[-2]['Hist'] if len(df_real) > 1 else 0
            momentum = "Ganando Fuerza" if abs(last_hist) > abs(prev_hist) else "Perdiendo Fuerza"
            
            # 3. AI Projection Logic
            proj_msg = "Sin predicción"
            forecast_signal = 0 # -1 Bearish, 0 Neutral, 1 Bullish
            
            if not df_proj.empty:
                last_proj = df_proj.iloc[-1]
                future_price = last_proj['venta']
                delta_proj = ((future_price - last_price) / last_price) * 100
                
                proj_msg = f"Objetivo 7d: ${future_price:.2f} ({delta_proj:+.2f}%)"
                if delta_proj > 0.5: forecast_signal = 1
                elif delta_proj < -0.5: forecast_signal = -1
            
            # 4. Action Signal (Hybrid)
            # Combine Technicals + Forecast
            action = "NEUTRAL (HOLD)"
            color = "gray"
            
            score = 0
            if is_bullish: score += 1
            if momentum == "Ganando Fuerza": score += 1
            score += forecast_signal # Add AI opinion
            
            if score >= 2:
                action = "COMPRAR (STRONG BUY)"
                color = "green"
            elif score <= -1: # Bearish trend + bearish forecast or momentum
                action = "VENDER (STRONG SELL)"
                color = "red"
            elif is_bullish and forecast_signal == 1:
                action = "COMPRAR (BUY)"
                color = "green"
                
            return {
                "trend": trend_str,
                "momentum": momentum,
                "projection": proj_msg,
                "action": action,
                "color": color,
                "price": last_price
            }
            
        except Exception as e:
            print(f"Analysis Error: {e}")
            return None

    def get_inspector_details(self, date_obj, currency_str=Moneda.USD.value):
        """Returns detailed stats for Inspector Panel."""
        db = SessionLocal()
        try:
            moneda = Moneda[currency_str]
            # Current
            curr = db.query(Cotizacion).filter_by(fecha=date_obj, moneda=moneda).first()
            if not curr: return None
            
            # Previous (for trend)
            prev = db.query(Cotizacion).filter(
                Cotizacion.fecha < date_obj, 
                Cotizacion.moneda == moneda
            ).order_by(Cotizacion.fecha.desc()).first()
            
            trend = "stable"
            prev_val = 0
            if prev:
                prev_val = prev.venta
                if curr.venta > prev.venta: trend = "up"
                elif curr.venta < prev.venta: trend = "down"
            
            # Spread
            # Spread
            spread = 0.0
            if curr.venta > 0:
                spread = ((curr.venta - curr.compra) / curr.venta) * 100
            
            return {
                "fecha": curr.fecha,
                "compra": curr.compra,
                "venta": curr.venta,
                "spread_pct": spread,
                "spread_abs": curr.venta - curr.compra,
                "trend": trend,
                "prev_venta": prev_val,
                "delta_abs": curr.venta - prev_val if prev else 0,
                "delta_pct": ((curr.venta - prev_val) / prev_val * 100) if prev and prev_val else 0
            }
        except Exception as e:
            app_logger.error(f"Inspector error: {e}")
            return None
        finally:
            db.close()

    def analyze_reconciliation(self, file_path, mapping_dict):
        """
        Analyzes CSV against DB and returns a Diff Report.
        Returns: Success (bool), Report (list of dicts)
        """
        db = SessionLocal()
        try:
            sep = self._detect_delimiter(file_path)
            df = pd.read_csv(file_path, sep=sep, encoding='utf-8', dtype=str)
            
            report = []
            
            col_date = mapping_dict.get('fecha')
            col_buy = mapping_dict.get('compra')
            col_sell = mapping_dict.get('venta')
            col_curr = mapping_dict.get('moneda')
            fixed_curr = mapping_dict.get('moneda_fixed', 'USD')
            
            currency_str = fixed_curr
            moneda_enum = Moneda[currency_str]

            for index, row in df.iterrows():
                try:
                    # 1. Date
                    date_val = parse_fuzzy_date(row[col_date])
                    if not date_val: continue
                    
                    # 2. Values
                    v_buy = 0.0
                    v_sell = 0.0
                    
                    if col_buy and col_buy in row:
                        val_compra = parse_localized_float(row[col_buy])
                    
                    if col_sell and col_sell in row:
                        val_venta = parse_localized_float(row[col_sell])
                        
                    # 3. Currency
                    curr_str = row.get(col_curr, fixed_curr)
                    if not curr_str: curr_str = "USD" # Fallback
                    
                    # Convert currency string to enum
                    try:
                        moneda_enum_row = Moneda[curr_str]
                    except KeyError:
                        app_logger.warning(f"Unknown currency '{curr_str}' in row. Skipping.")
                        continue
                        
                    # DB Check
                    existing = db.query(Cotizacion).filter_by(fecha=date_val, moneda=moneda_enum_row).first()
                    
                    status = "NEW"
                    db_val_compra = 0.0
                    db_val_venta = 0.0
                    
                    if existing:
                        db_val_compra = existing.compra
                        db_val_venta = existing.venta
                        # Compare (Tolerance for float?)
                        if abs(existing.venta - val_venta) < 0.01 and abs(existing.compra - val_compra) < 0.01:
                            status = "MATCH"
                        else:
                            status = "CONFLICT"
                            
                    report.append({
                        "fecha": date_val,
                        "moneda": currency_str,
                        "csv_compra": val_compra,
                        "csv_venta": val_venta,
                        "db_compra": db_val_compra,
                        "db_venta": db_val_venta,
                        "status": status
                    })

                except Exception as row_e:
                    # Log but continue
                    pass
            
            return True, report

        except Exception as e:
            app_logger.error(f"Reconciliation failed: {e}")
            return False, str(e)
        finally:
            db.close()


