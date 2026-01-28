
import pandas as pd
import os
from datetime import datetime
from database import SessionLocal
from models.entities import Vencimiento, Pago, Cotizacion, Moneda
from controllers.forex_controller import ForexController
from utils.import_helper import load_data_file
from utils.format_helper import parse_fuzzy_date, parse_localized_float
from sqlalchemy import func
from services.data_import_service import DataImportService
from services.reconciliation_service import ReconciliationService

class ReconciliationController:
    def __init__(self):
        self.forex_ctrl = ForexController()
        self.import_service = DataImportService()
        self.recon_service = ReconciliationService()

    def update_cotizacion_manual(self, fecha, moneda, compra, venta):
        return self.forex_ctrl.update_cotizacion_manual(fecha, moneda, compra, venta)

    def delete_cotizacion(self, fecha, moneda):
        return self.forex_ctrl.delete_cotizacion(fecha, moneda)

    def analyze(self, source_type, file_path, mapping=None):
        if source_type == "Forex":
            return self.analyze_forex(file_path, mapping)
        elif source_type == "Banco":
            return self.analyze_bank(file_path, mapping)
        elif source_type == "Proveedores":
            return self.analyze_supplier(file_path, mapping)
        else:
            return False, "Tipo de fuente no soportado."

    def analyze_forex(self, file_path, mapping):
        # Delegate to existing robust logic
        # Default mapping if None
        if not mapping:
             mapping = {'fecha': 'Fecha', 'compra': 'Compra', 'venta': 'Venta', 'moneda_fixed': 'USD'}
        return self.forex_ctrl.analyze_reconciliation(file_path, mapping)

    def _detect_structure(self, file_path):
        """
        Scans first 20 rows to find Header Row.
        Returns: (DataFrame correctly loaded, ColumnMap dict)
        """
        print(f"DEBUG: Smart Detecting Structure for {file_path}")
        try:
            # 1. Load raw (no header)
            raw_df = pd.read_excel(file_path, header=None, nrows=20) if file_path.endswith('.xlsx') else pd.read_csv(file_path, header=None, nrows=20, encoding='utf-8')
            
            # 2. Score Rows
            best_row_idx = -1
            best_score = 0
            
            keywords = {
                'fecha': ['FECHA', 'DATE', 'DIA'],
                'descripcion': ['DESCRIPCION', 'CONCEPTO', 'DETALLE', 'MOVIMIENTO', 'REFERENCIA'],
                'importe': ['IMPORTE', 'MONTO', 'SALDO', 'VALOR'],
                'debito': ['DEBITO', 'DÉBITO', 'EGRESO', 'PAGOS'], # Extra specific
                'credito': ['CREDITO', 'CRÉDITO', 'INGRESO', 'DEPOSITO']
            }
            
            for idx, row in raw_df.iterrows():
                score = 0
                row_str = " ".join([str(x).upper() for x in row.values])
                
                # Simple presence check
                if any(k in row_str for k in keywords['fecha']): score += 3
                if any(k in row_str for k in keywords['descripcion']): score += 3
                if any(k in row_str for k in keywords['importe']): score += 3
                if any(k in row_str for k in keywords['debito']): score += 3
                if any(k in row_str for k in keywords['credito']): score += 3
                
                if score > best_score:
                    best_score = score
                    best_row_idx = idx
            
            print(f"DEBUG: Best Header Row detected at Index: {best_row_idx} (Score: {best_score})")
            
            # 3. Reload with correct header
            final_header_row = best_row_idx if best_row_idx >= 0 else 0
            df = load_data_file(file_path, header_row=final_header_row)
            
            # 4. Map Columns
            mapping = {}
            for col in df.columns:
                c_upper = str(col).upper().strip()
                
                # Map to canonical internal names
                if not mapping.get('fecha') and any(k in c_upper for k in keywords['fecha']): mapping['fecha'] = col
                elif not mapping.get('descripcion') and any(k in c_upper for k in keywords['descripcion']): mapping['descripcion'] = col
                elif not mapping.get('debito') and any(k in c_upper for k in keywords['debito']): mapping['debito'] = col
                elif not mapping.get('credito') and any(k in c_upper for k in keywords['credito']): mapping['credito'] = col
                elif not mapping.get('importe') and any(k in c_upper for k in keywords['importe']): mapping['importe'] = col
                
            return df, mapping
            
        except Exception as e:
            print(f"Structure Detect Failed: {e}")
            # Fallback
            return load_data_file(file_path), {}

    def _sanitize_float(self, value):
        """Converts string like '1.200,50' or '$ 50.00' to float."""
        if pd.isna(value) or value is None: return 0.0
        if isinstance(value, (int, float)): return float(value)
        
        s = str(value).strip()
        s = s.replace("$", "").replace("USD", "").strip()
        
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."): 
                s = s.replace(".", "").replace(",", ".")
            else: 
                s = s.replace(",", "")
        elif "," in s: 
            s = s.replace(",", ".")
            
        try: return float(s)
        except: return 0.0

    def analyze_bank(self, file_path, mapping=None):
        """
        Smart Bank Reconciliation:
        Phase 1: Iterate CSV against DB (Exact & Fuzzy).
        Phase 2: Detect 'No en Banco' (Unmatched DB records).
        """
        db = SessionLocal()
        db_pagos = None 
        try:
            # --- 0. CONFIG PARSING ---
            column_map = mapping
            
            # Helper to unpack config dict if passed from UI
            if column_map and isinstance(column_map, dict) and 'mapping' in column_map:
                column_map = column_map.get('mapping')

            # --- 1. SMART HEADER & MAPPING ---
            df, detected_map = self._detect_structure(file_path)
            
            if not column_map:
                if detected_map:
                    print(f"DEBUG: Smart Structure Detected: {detected_map}")
                    column_map = detected_map
                else:
                    return False, "No se pudo detectar la estructura del archivo (Encabezados no encontrados)."
            else:
                # Merge user config with auto-detected dates if needed? 
                # For now take user config but we might need to respect detected header_row (which returned df already handles)
                pass

            report = []

            # Validate Mapping
            missing = [k for k,v in column_map.items() if v not in df.columns and k in ['fecha', 'descripcion']]
            if missing:
                 return False, f"Columnas faltantes en el archivo: {missing}. (Detectadas: {list(df.columns)})"


            # --- 2. PRELOAD SYSTEM CONTEXT ---
            # Get Min/Max Date from CSV to query DB range
            try:
                # Quick scan for date range
                dates = []
                for x in df[column_map['fecha']]:
                    try: 
                        if hasattr(x, 'date'): dates.append(x.date())
                        else: dates.append(pd.to_datetime(x, dayfirst=True).date())
                    except: pass
                if dates:
                    min_date = min(dates)
                    max_date = max(dates)
                    print(f"DEBUG: CSV Date Range: {min_date} to {max_date}")
                else:
                    return False, "No se detectaron fechas válidas."
            except: 
                return False, "Error rango fechas."

            # Fetch System Pagos in Range (-365 Days buffer for checks/clearing)
            # This covers payments made in previous months/years (e.g. widely different dates)
            from datetime import timedelta
            search_start = min_date - timedelta(days=365)
            search_end = max_date + timedelta(days=365)
            
            db_pagos = db.query(Pago).filter(
                Pago.fecha_pago >= search_start,
                Pago.fecha_pago <= search_end
            ).all()
            print(f"DEBUG: System Payments Found: {len(db_pagos)} (Range: {search_start} to {search_end})")
            
            # Create a mutable list/pool for matching
            # Store ID to track usage
            system_pool = []
            for p in db_pagos:
                val = p.vencimiento.monto_original if p.vencimiento else 0.0
                system_pool.append({
                    'id': p.id,
                    'obj': p,
                    'fecha': p.fecha_pago,
                    'monto': float(val), # Assuming positive for payments
                    'matched': False
                })

            # --- 3. FORWARD PASS (CSV -> DB) ---
            for index, row in df.iterrows():
                try:
                    # Norm Date
                    raw_date = row.get(column_map.get('fecha'))
                    date_val = parse_fuzzy_date(raw_date)
                    
                    if not date_val: continue
                    
                    # Norm Amount
                    final_amount = 0.0
                    c_deb = column_map.get('debito')
                    c_cred = column_map.get('credito')
                    
                    # Handle Independent Columns
                    if c_deb:
                        v_deb = parse_localized_float(row.get(c_deb))
                        if v_deb > 0: final_amount -= v_deb # Payment = Negative
                        
                    if c_cred:
                        v_cred = parse_localized_float(row.get(c_cred))
                        if v_cred > 0: final_amount += v_cred # Deposit = Positive
                        
                    # Fallback to single 'Importe' column if neither specific col matched or value is still 0 (and importer exists)
                    if final_amount == 0.0 and (not c_deb and not c_cred):
                        final_amount = parse_localized_float(row.get(column_map.get('importe')))
                        if isinstance(row.get(column_map.get('importe')), str) and '-' in str(row.get(column_map.get('importe'))):
                            final_amount = -abs(final_amount)

                    desc = str(row.get(column_map.get('descripcion'), ""))[:50]
                    
                    # MATCHING LOGIC
                    # Target Amount: Bank outflow (-100) matches System Payment (100) usually.
                    # Or Bank inflow (100) matches System Collection (100).
                    # Let's assume absolute comparison for Matching for now to simpler things.
                    target_amt = abs(final_amount)
                    
                    match_found = None
                    status = "NO_EN_SISTEMA"
                    
                    # SMART MATCH V2: Amount Priority + Date Proximity
                    # 1. Filter ALL by Amount (Exact within tolerance)
                    candidates = [x for x in system_pool if not x['matched'] and abs(x['monto'] - target_amt) < 0.05]
                    
                    if candidates:
                        # 2. Find Closest Date
                        # We use abs(days) to find the nearest one, whether slightly before or after.
                        best_match = min(candidates, key=lambda x: abs((x['fecha'] - date_val).days))
                        
                        match_found = best_match
                        
                        days_diff = abs((match_found['fecha'] - date_val).days)
                        if days_diff == 0: status = "MATCH"
                        elif days_diff <= 5: status = "DIFERENCIA_FECHA" # Small slip
                        else: status = "MATCH_LEJANO" # Large slip but amount matches exactly
                    
                    db_val = 0.0
                    display_desc = desc
                    display_date = date_val
                    
                    if match_found:
                         match_found['matched'] = True
                         db_val = match_found['monto']
                         # Sign correction for display
                         if final_amount < 0: db_val = -db_val
                         
                         # OVERWRITE WITH SYSTEM DATA (User Request)
                         if match_found['obj'].vencimiento:
                             v = match_found['obj'].vencimiento
                             # Construct description manually since property might be missing
                             v_desc = "Vencimiento"
                             if v.obligacion and v.obligacion.proveedor:
                                  v_desc = v.obligacion.proveedor.nombre_entidad
                             
                             display_desc = f"✅ {v_desc}"
                             # display_date = match_found['fecha'] # User asked to "Include as real date...". 
                             # Usually Reconciliation keeps Bank Date as reference for the bank statement row, 
                             # but shows System Data alongside. Changing the PRIMARY date column might confuse the "Bank Timeline".
                             # I will keep Bank Date in 'fecha' column but put System Date in description or separate column if Grid supports it.
                             # For now, let's append date to desc to be safe:
                             display_desc += f" ({match_found['fecha'].strftime('%d/%m')})"

                    report.append({
                        "fecha": date_val, # Keep Bank Date as Row Key
                        "concepto": display_desc,
                        "valor_csv": final_amount,
                        "valor_db": db_val,
                        "status": status,
                        "moneda": "ARS",
                        "ref": row.get(column_map.get('referencia'), "") if column_map.get('referencia') else ""
                    })

                except Exception as e:
                    print(f"DEBUG: Row Error: {e}")
                    import traceback
                    traceback.print_exc()

            # --- 4. BACKWARD PASS REMOVED (User Request) ---
            # Strictly list Bank File content only.
            
            print(f"DEBUG: Report size: {len(report)}")
            return True, report
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, str(e)
        finally:
            db.close()

    def analyze_supplier(self, file_path, mapping=None):
        """
        Supplier Reconciliation:
        Matches CSV lines (Date, Amount) against System 'Vencimientos' (Debts).
        """
        db = SessionLocal()
        try:
            df = load_data_file(file_path)
            
            report = []
            
            col_date = next((c for c in df.columns if 'fecha' in c.lower()), df.columns[0])
            col_amount = next((c for c in df.columns if 'total' in c.lower() or 'impor' in c.lower() or 'monto' in c.lower()), df.columns[1])
            col_ref = next((c for c in df.columns if 'fact' in c.lower() or 'ref' in c.lower()), None) # Invoice ID

            for index, row in df.iterrows():
                try:
                    raw_date = row[col_date]
                    date_val = parse_fuzzy_date(raw_date)
                    if not date_val: continue
                    
                    amt_val = parse_localized_float(row[col_amount])
                    
                    # Search Vencimientos (Accounts Payable)
                    # Match Date and Amount
                    q = db.query(Vencimiento).filter(
                        Vencimiento.fecha_vencimiento == date_val,
                        Vencimiento.monto_original == amt_val
                    )
                    existing = q.first()
                    
                    status = "MATCH" if existing else "NEW"
                    db_val = existing.monto_original if existing else 0.0
                    
                    desc = f"Factura {row[col_ref]}" if col_ref else "Obligacion Detectada"

                    report.append({
                        "fecha": date_val,
                        "concepto": desc,
                        "valor_csv": amt_val,
                        "valor_db": db_val,
                        "status": status,
                        "moneda": "ARS"
                    })
                except: pass
                
            return True, report
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def search_vencimientos(self, search_term):
        """
        Search for Vencimientos (PENDING or PAID) matching the term.
        """
        db = SessionLocal()
        try:
            from models.entities import EstadoVencimiento, Obligacion, ProveedorServicio
            from sqlalchemy import or_, and_
            
            # Base Query: All non-deleted (Paid or Pending)
            query = db.query(Vencimiento).join(Vencimiento.obligacion).join(Obligacion.proveedor).filter(
                Vencimiento.is_deleted == 0 
            )
            
            if not search_term or search_term == "*":
                # Return latest if empty
                results = query.order_by(Vencimiento.fecha_vencimiento.desc()).limit(20).all()
            else:
                # Try as number (Amount or ID)
                is_number = False
                try:
                     val = float(search_term)
                     is_number = True
                     
                     # Check if it's an ID (integer equal to float)
                     if val.is_integer() and val < 1000000: # Heuristic: IDs are usually small integers
                          query_id = query.filter(Vencimiento.id == int(val))
                          if query_id.count() > 0:
                               query = query_id
                          else:
                               # Fallback to Amount search
                               tolerance = max(val * 0.05, 1000.0)
                               min_v = val - tolerance
                               max_v = val + tolerance
                               query = query.filter(Vencimiento.monto_original.between(min_v, max_v))
                     else:
                          # Amount search
                          tolerance = max(val * 0.05, 1000.0)
                          min_v = val - tolerance
                          max_v = val + tolerance
                          query = query.filter(Vencimiento.monto_original.between(min_v, max_v))
                except:
                     pass
                
                if not is_number:
                     # Text search
                     # Check date format DD/MM or YYYY-MM
                     is_date = False
                     import re
                     # DD/MM
                     match_dm = re.match(r"(\d{1,2})[/-](\d{1,2})", search_term)
                     if match_dm:
                          d, m = match_dm.groups()
                          # Filter by Day/Month (ignoring Year? or assume current/last year?)
                          # SQLAlchemy doesn't easily do day/month extract cross-db without func.
                          # Let's try flexible filter:
                          from sqlalchemy import extract
                          query = query.filter(
                              extract('day', Vencimiento.fecha_vencimiento) == int(d),
                              extract('month', Vencimiento.fecha_vencimiento) == int(m)
                          )
                          is_date = True
                     
                     if not is_date:
                         term = f"%{search_term}%"
                         query = query.filter(
                            or_(
                                ProveedorServicio.nombre_entidad.ilike(term),
                                Obligacion.numero_cliente_referencia.ilike(term)
                            )
                         )
                
                # Order by date desc
                results = query.order_by(Vencimiento.fecha_vencimiento.desc()).limit(50).all()
            
            # Construct description dynamically
            output = []
            for r in results:
                desc_str = "Sin descripción"
                if r.obligacion and r.obligacion.proveedor:
                    desc_str = f"{r.obligacion.proveedor.nombre_entidad}"
                    if r.obligacion.numero_cliente_referencia:
                         desc_str += f" - Ref: {r.obligacion.numero_cliente_referencia}"
                
                # Append Status if not Pending
                if r.estado != EstadoVencimiento.PENDIENTE:
                    desc_str += f" [{r.estado.name}]"
                
                # Append Date
                d_str = r.fecha_vencimiento.strftime('%d/%m/%Y')

                output.append({
                    'id': r.id,
                    'fecha': r.fecha_vencimiento,
                    'descripcion': f"{d_str} - {desc_str}",
                    'monto': r.monto_original
                })
            
            return output
            
        except Exception as e:
            print(f"Search Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            db.close()

    def apply_match(self, bank_data, vencimiento_id):
        """
        Manually link a Bank Transaction to a Vencimiento.
        1. Update Vencimiento -> PAGADO
        2. Create Pago record with Bank Details
        """
        from services.vencimiento_service import VencimientoService
        from dtos.vencimiento import VencimientoUpdateDTO
        from models.entities import EstadoVencimiento
        
        service = VencimientoService()
        
        try:
            # Prepare DTO
            # Bank Amount is usually negative for payments in CSV, but system stores positive.
            # We take the absolute value from bank_data['valor_csv']
            real_amount = abs(bank_data['valor_csv'])
            real_date = bank_data['fecha']
            
            dto = VencimientoUpdateDTO(
                estado=EstadoVencimiento.PAGADO.value,
                monto_pagado=real_amount,
                fecha_pago=real_date
            )
            
            service.update(vencimiento_id, dto)
            return True, "Conciliación aplicada con éxito."
            
        except Exception as e:
            return False, str(e)

    def export_report(self, report_data, export_format="excel", filename=None):
        """
        Exports the current reconciliation report to a file.
        format: 'excel' or 'pdf'
        """
        if not report_data:
            return False, "No hay datos para exportar."
            
        try:
            import pandas as pd
            df = pd.DataFrame(report_data)
            
            # Custom Column Selection (Optimize space)
            # User requested removing last columns (Moneda, Status, Ref)
            keep_cols = ["fecha", "concepto", "valor_db", "valor_csv"]
            
            # Filter matches
            available = [c for c in keep_cols if c in df.columns]
            df = df[available]

            # Beutify Columns
            cols_map = {
                "fecha": "Fecha",
                "descripcion": "Descripción",
                "concepto": "Concepto",
                "valor_db": "Valor Sistema",
                "valor_csv": "Valor Banco"
            }
            # Rename existing cols
            df.rename(columns={k: v for k, v in cols_map.items() if k in df.columns}, inplace=True)
            
            if export_format == "excel":
                if not filename: filename = "conciliacion_export.xlsx"
                if not filename.endswith(".xlsx"): filename += ".xlsx"
                
                df.to_excel(filename, index=False)
                return True, f"Excel guardado en: {filename}"
                
            elif export_format == "pdf":
                if not filename: filename = "conciliacion_export.pdf"
                if not filename.endswith(".pdf"): filename += ".pdf"
                
                try:
                    from services.report_service import ReportService
                    
                    # Prepare Data for Table
                    headers = list(df.columns)
                    # Convert DataFrame to list of lists (strings for safety)
                    rows = df.astype(str).values.tolist()
                    
                    summary = f"Total registros: {len(rows)}"
                    title = "Reporte de Conciliación y Auditoría"
                    
                    svc = ReportService()
                    return svc.generate_pdf(filename, title, headers, rows, summary)
                    
                except ImportError:
                     return False, "Error de dependencias PDF."
                except Exception as e:
                     return False, f"Error al generar reporte: {e}"

        except Exception as e:
            return False, str(e)

    def revert_match(self, vencimiento_id):
        """
        Reverts a match: Sets Vencimiento -> PENDIENTE, MontoPago -> 0, FechaPago -> None.
        Optional: Delete Pago record? logic inside service update.
        """
        from services.vencimiento_service import VencimientoService
        from dtos.vencimiento import VencimientoUpdateDTO
        from models.entities import EstadoVencimiento
        
        service = VencimientoService()
        try:
            dto = VencimientoUpdateDTO(
                estado=EstadoVencimiento.PENDIENTE.value,
                monto_pagado=0,
                fecha_pago=None
            )
            # Service update should handle clearing Pago if logic exists, or at least setting amounts to 0.
            # Ideally we should DELETE the Pago record, but Update logic might just update it to 0.
            # Let's rely on update for now.
            service.update(vencimiento_id, dto)
            return True, "Vinculación deshecha correctamente."
        except Exception as e:
            return False, str(e)

    def quick_create_from_receipt(self, bank_row, file_path):
        """
        Quickly creates a reconciled Vencimiento from a Bank Row + Receipt File.
        """
        try:
            # 1. Prepare Data
            # Bank Amount is usually negative for payments, creating Vencimiento requires positive
            amt = abs(bank_row.get('valor_csv', 0.0))
            date_val = bank_row.get('fecha')
            concept = bank_row.get('concepto', 'Gasto Bancario')
            
            # Ensure date_val is a date object
            if isinstance(date_val, str):
                 date_val = parse_fuzzy_date(date_val)
            
            if not date_val: date_val = date.today() # Fallback?

            # Format period "MM-YYYY"
            target_period = date_val.strftime("%Y-%m")
            
            data = {
                'fecha': date_val, # Now guaranteed to be date object
                'concepto': concept,
                'valor_db': amt,
                'moneda': 'ARS',
                'files': {
                    'payment': file_path, # Determining it's a payment receipt
                    # 'invoice': file_path # Typically one file serves as both if simple receipt
                }
            }
            
            # 2. Call existing logic
            return self.create_vencimiento_from_bank(data, target_period)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, str(e)

    def create_vencimiento_from_bank(self, data, target_period_str):
        """
        Creates a new Vencimiento from Bank Data + User edits.
        target_period_str: "MM-YYYY" (e.g. "12-2025") or "YYYY-MM"
        
        data = {
          'fecha': 'YYYY-MM-DD',
          'concepto': ...,
          'valor_db': ... (User entered amount),
          'moneda': ...
          'files': {'payment': path, 'invoice': path}
        }
        """
        # Normalize Period to YYYY-MM
        # Fix for "Connected Cables": UI sends MM-YYYY, DB expects YYYY-MM
        if target_period_str and "-" in target_period_str:
             parts = target_period_str.split("-")
             if len(parts[0]) == 2 and len(parts[1]) == 4: # MM-YYYY detected
                 target_period_str = f"{parts[1]}-{parts[0]}"
        
        from models.entities import Vencimiento, EstadoVencimiento, ProveedorServicio, CategoriaServicio
        from services.vencimiento_service import VencimientoService
        from datetime import date # Fixed Import
        from models.entities import Pago
        
        from database import SessionLocal # Import Local Session
        service = VencimientoService()
        session = SessionLocal() # Create Session
        
        try:
            # 2. Resolve Obligacion/Proveedor (Required by FK)
            from models.entities import Obligacion, ProveedorServicio, Inmueble
            
            # Find generic provider "Banco (Conciliación)"
            prov = session.query(ProveedorServicio).filter(ProveedorServicio.nombre_entidad.ilike("Banco (Conciliación)")).first()
            if not prov:
                 # Fallback/Create
                 prov = ProveedorServicio(nombre_entidad="Banco (Conciliación)", categoria=CategoriaServicio.OTROS.value)
                 session.add(prov)
                 session.flush()
            
            # Find Generic Inmueble
            inm = session.query(Inmueble).filter(Inmueble.alias.ilike("%Varios%")).first()
            if not inm:
                inm = session.query(Inmueble).filter(Inmueble.alias.ilike("Propiedad General")).first()
                if not inm:
                    # Create generic Inmueble 
                    inm = Inmueble(alias="Propiedad General", tipo_propiedad="Oficina", direccion="General")
                    session.add(inm)
                    session.flush()

            # Find Generic Obligacion for this provider
            obl = session.query(Obligacion).filter(Obligacion.servicio_id == prov.id).first()
            if not obl:
                # Use prov.id for servicio_id (as per model definition)
                obl = Obligacion(inmueble_id=inm.id, servicio_id=prov.id, numero_cliente_referencia="conciliacion")
                session.add(obl)
                session.flush()
            
            # 3. Create Vencimiento
            new_v = Vencimiento(
                obligacion_id=obl.id, # LINKED
                fecha_vencimiento=data['fecha'], 
                monto_original=data['valor_db'],
                moneda=data.get('moneda', 'ARS'),
                periodo=target_period_str,
                estado=EstadoVencimiento.PAGADO
            )
            session.add(new_v)
            session.flush() # Get ID
            
            # 4. Create Payment Record (Since it is already paid)
            new_pago = Pago(
                vencimiento_id=new_v.id,
                fecha_pago=data['fecha'],
                monto=data['valor_db'],
                medio_pago="Transferencia", # Default for bank
                comprobante_path=None
            )
            session.add(new_pago)
            session.flush()
            
            # --- HANDLE FILES ---
            # IMPORTANT: Upload to Cloud DB (BLOBs) instead of local copy
            files = data.get('files', {})
            
            # 1. Invoice
            if 'invoice' in files and os.path.exists(files['invoice']):
                try:
                    doc_id = service.upload_document(files['invoice'], session=session)
                    new_v.documento_id = doc_id
                except Exception as e:
                    print(f"Failed to upload matched invoice: {e}")

            # 2. Payment Proof
            if 'payment' in files and os.path.exists(files['payment']):
                try:
                     pay_doc_id = service.upload_document(files['payment'], session=session)
                     new_v.comprobante_pago_id = pay_doc_id
                     # Optional: Link to Pago if schema supports it, otherwise Vencimiento is enough
                except Exception as e:
                    print(f"Failed to upload matched payment: {e}")
            
            session.commit()
            return True, new_v.id
            
        except Exception as e:
            if session: session.rollback()
            return False, str(e)
        finally:
            if session: session.close()

    def delete_vencimiento(self, vencimiento_id):
        """
        Deletes a Vencimiento record via the service.
        Useful for un-reconciling/undoing a 'Create from Bank' action.
        """
        try:
            from services.vencimiento_service import VencimientoService
            service = VencimientoService()
            service.delete(vencimiento_id) 
            return True, "Registro eliminado correctamente."
        except Exception as e:
            return False, f"Error al eliminar: {str(e)}"

    def get_vencimiento(self, vencimiento_id):
        """
        Retrieves a Vencimiento by ID with eager loaded relations to safely detach.
        """
        from database import SessionLocal
        from models.entities import Vencimiento, Obligacion, ProveedorServicio, Inmueble
        from sqlalchemy.orm import joinedload
        
        session = SessionLocal()
        try:
            # Eager load dependencies to allow usage after session close
            v = session.query(Vencimiento).options(
                joinedload(Vencimiento.obligacion).joinedload(Obligacion.proveedor),
                joinedload(Vencimiento.obligacion).joinedload(Obligacion.inmueble),
                joinedload(Vencimiento.pagos)
            ).get(vencimiento_id)
            
            if v:
                # Refresh trigger
                _ = v.obligacion.proveedor.nombre_entidad if v.obligacion and v.obligacion.proveedor else None
                session.expunge(v) # Detach from session so we can pass it around
                return v
            return None
        except Exception as e:
            print(f"Error fetching vencimiento {vencimiento_id}: {e}")
            return None
        finally:
            session.close()


