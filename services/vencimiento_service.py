import shutil
import os
from uuid import uuid4
from typing import List, Optional
from datetime import date

from config import DOCS_DIR
from utils.decorators import safe_transaction
from utils.exceptions import ServiceError
from utils.logger import app_logger
from models.entities import Vencimiento, EstadoVencimiento, Obligacion, Pago
from repositories.vencimiento_repository import VencimientoRepository
from services.audio_service import AudioService
from dtos.vencimiento import VencimientoCreateDTO, VencimientoUpdateDTO
import pandas as pd
from datetime import datetime

class VencimientoService:
    def __init__(self):
        self.audio = AudioService()

    @safe_transaction
    def import_from_dataframe(self, df, mapping_dict, session=None) -> tuple[int, list]:
        """
        Imports Vencimientos from DF.
        Mapping must include: 'fecha', 'monto', 'descripcion'.
        Optional: 'entidad' (Proveedor).
        RETURNS: (success_count, errors_list)
        """
        success_count = 0
        errors = []
        
        # Pre-fetch all Obligations for matching (Alias -> ID map)
        # Using a tuple key (alias, proveedor_id) might be safer, but let's stick to Alias or Description matching
        all_obs = session.query(Obligacion).all()
        # Build Lookup Map: Alias (LowerCase) -> Obligacion
        # Also map: Proveedor Name -> [Obligaciones] (for fuzzy match)
        
        obs_map = {o.inmueble.alias.lower(): o for o in all_obs if o.inmueble and o.inmueble.alias}
        # Also map by Obligacion unique description if we had one? 
        # Currently Obligacion is Inmueble(Servicio) + Proveedor.
        # Let's map "Servicio - Proveedor" string?
        
        # Better: We need to find the Obligacion based on the CSV Description.
        # Strategy:
        # 1. Exact match on Obligacion.id (if provided? unlikely)
        # 2. Fuzzy match Description against "Proveedor Name" or "Servicio Alias"
        
        # Let's create a list of keywords for each obligation
        # kw_map = [ (obl, ["fibertel", "internet", "claro"]) ]
        
        # [OPTIMIZATION] Batch Existence Check
        # 1. Determine Date Range to fetch existing records cleanly
        try:
            # Create a temp copy to parse dates safely for range determination
            col_fecha = mapping_dict.get('fecha')
            temp_dates = []
            
            for val in df[col_fecha]:
                try:
                    d = None
                    if isinstance(val, (datetime, date)): d = val
                    else: d = pd.to_datetime(val, dayfirst=True).date()
                    if d: temp_dates.append(d)
                except: pass
            
            existing_cache = set()
            if temp_dates:
                min_date = min(temp_dates)
                max_date = max(temp_dates)
                
                # Fetch all potential duplicates in one query
                range_dupes = session.query(Vencimiento).filter(
                    Vencimiento.fecha_vencimiento >= min_date,
                    Vencimiento.fecha_vencimiento <= max_date,
                    Vencimiento.is_deleted == 0
                ).all()
                
                # Build Cache: (obligacion_id, date, monto)
                # Note: Float comparison in tuple key is risky, but monto_original comes from DB
                for v in range_dupes:
                    existing_cache.add((v.obligacion_id, v.fecha_vencimiento, float(v.monto_original)))

        except Exception as e:
            app_logger.warning(f"Optimization Pre-fetch failed: {e}. Falling back to row-by-row might be slow but safe.")
            existing_cache = set()

        from models.entities import Proveedor
        
        for index, row in df.iterrows():
            try:
                # 1. Parse Date
                col_fecha = mapping_dict.get('fecha')
                raw_date = row[col_fecha]
                if pd.isna(raw_date): continue
                
                date_val = None
                try: 
                    date_val = pd.to_datetime(raw_date, dayfirst=True).date()
                except:
                    # Try manual parse
                    s = str(raw_date).strip().split(" ")[0]
                    date_val = datetime.strptime(s, "%d/%m/%Y").date()
                
                if not date_val: continue

                # 2. Parse Amount
                col_monto = mapping_dict.get('monto')
                # Reuse util from somewhere or implement simple clean
                val_str = str(row[col_monto])
                val_str = val_str.replace("$", "").replace("USD", "").replace("ARS", "").strip()
                # Handle 1.000,00 vs 1,000.00
                if "," in val_str and "." in val_str:
                    if val_str.rfind(",") > val_str.rfind("."): # 1.000,00
                        val_str = val_str.replace(".", "").replace(",", ".")
                    else: # 1,000.00
                        val_str = val_str.replace(",", "")
                elif "," in val_str: val_str = val_str.replace(",", ".")
                
                monto = float(val_str)
                
                # 3. Find Obligacion
                col_desc = mapping_dict.get('descripcion')
                desc = str(row[col_desc]).lower()
                
                col_ent = mapping_dict.get('entidad')
                ent_name = str(row[col_ent]).lower() if col_ent else ""
                
                target_obl = None
                
                # Heuristic A: Look for Proveedor Name in Entidad or Description
                # This is O(N*M), but N (Obligations) is small (<100 likely)
                best_score = 0
                
                for obl in all_obs:
                    score = 0
                    p_name = obl.proveedor.nombre_entidad.lower()
                    if p_name in ent_name or p_name in desc: score += 5
                    
                    s_name = obl.servicio.nombre_servicio.lower() if obl.servicio else ""
                    if s_name and (s_name in desc): score += 3
                    
                    if obl.inmueble and (obl.inmueble.alias.lower() in desc): score += 2
                    
                    if score > best_score and score >= 3:
                        best_score = score
                        target_obl = obl
                
                if not target_obl:
                    # Fallback: Look for "Varios" or Generic?
                    # Or Create New? Creating new is risky without correct IDs.
                    # We skip and report error.
                    errors.append(f"Fila {index}: No se encontró Obligación para '{desc}' / '{ent_name}'")
                    continue
                    
                # 4. Create Vencimiento
                # Check duplicate using Cache (O(1)) instead of DB Query
                
                # Check exact match
                if (target_obl.id, date_val, monto) in existing_cache:
                     errors.append(f"Fila {index}: Ya existe (Omitido por Caché).")
                     continue

                # Safety fall-back check if cache was empty? 
                # No, better trust cache if populated.
                
                # If not in cache, we assume it doesn't exist.
                # Adding to cache dynamically if we process duplicates within the SAME import file?
                # Yes, good point.
                
                if (target_obl.id, date_val, monto) in existing_cache:
                    continue
                else:
                    existing_cache.add((target_obl.id, date_val, monto)) # Prevent duplicates within CSV itself

                    
                new_venc = Vencimiento(
                    obligacion_id=target_obl.id,
                    periodo=f"{date_val.year}-{date_val.month:02d}",
                    fecha_vencimiento=date_val,
                    monto_original=monto,
                    estado=EstadoVencimiento.PENDIENTE,
                    ruta_archivo_pdf=None
                )
                session.add(new_venc)
                success_count += 1
                
            except Exception as e:
                errors.append(f"Fila {index}: Error {str(e)}")

        return success_count, errors

    def _get_repo(self, session):
        return VencimientoRepository(session, Vencimiento)

    @safe_transaction
    def get_all(self, inmueble_id=None, estado=None, period_id=None, limit=None, offset=None, session=None) -> tuple[List[Vencimiento], int]:
        repo = self._get_repo(session)
        items, count = repo.get_details_all(inmueble_id, estado, period_id, limit, offset)
        
        # Critical: Expunge to survive session close
        for i in items:
            session.expunge(i)
            
        return items, count

    @safe_transaction
    def get_by_id(self, id: int, session=None) -> Optional[Vencimiento]:
        repo = self._get_repo(session)
        return repo.get_by_id(id)

    @safe_transaction
    def get_with_relations(self, id: int, session=None) -> Optional[Vencimiento]:
        repo = self._get_repo(session)
        venc = None
        if hasattr(repo, 'get_with_relations'):
            venc = repo.get_with_relations(id)
        else:
            venc = repo.get_by_id(id)
            
        if venc:
            # Force load of relations if not covered by repo strategy (Double check)
            # Accessing them here while session is open prevents lazy load fail later if not joined.
            # But repo.get_with_relations should have joinedload.
            # Crucial: Expunge to prevent 'expire_on_commit' from invalidating the data
            _ = venc.pagos
            _ = venc.obligacion
            if venc.obligacion:
                _ = venc.obligacion.inmueble
                _ = venc.obligacion.proveedor
            
            session.expunge(venc)
            
        return venc

    @safe_transaction
    def create(self, dto: VencimientoCreateDTO, session=None) -> Vencimiento:
        repo = self._get_repo(session)
        
        final_path = None
        if dto.ruta_archivo_pdf:
             # Query Obligacion for naming
             obl = session.query(Obligacion).get(dto.obligacion_id)
             if obl:
                 final_path = self._save_pdf_structured(
                     dto.ruta_archivo_pdf, dto.periodo, obl.inmueble.alias, obl.proveedor.nombre_entidad, "FACTURA"
                 )
        
        final_path_payment = None
        if dto.ruta_comprobante_pago:
             obl = session.query(Obligacion).get(dto.obligacion_id) # Optimization: query only if not already queried
             if obl:
                 final_path_payment = self._save_pdf_structured(
                     dto.ruta_comprobante_pago, dto.periodo, obl.inmueble.alias, obl.proveedor.nombre_entidad, "PAGO"
                 )

        entity = Vencimiento(
            obligacion_id=dto.obligacion_id,
            periodo=dto.periodo,
            fecha_vencimiento=dto.fecha_vencimiento,
            monto_original=dto.monto_original,
            estado=dto.estado,
            ruta_archivo_pdf=final_path,
            ruta_comprobante_pago=final_path_payment,
            documento_id=dto.documento_id,
            comprobante_pago_id=dto.comprobante_pago_id
        )
        return repo.add(entity)

    @safe_transaction
    def upload_document(self, file_path: str, session=None) -> int:
        """Reads file and saves to Documento table. Returns ID."""
        import os
        from models.entities import Documento
        
        if not os.path.exists(file_path):
            raise ServiceError(f"File not found: {file_path}")
            
        filename = os.path.basename(file_path)
        size = os.path.getsize(file_path)
        
        # Determine Mime Type
        ext = os.path.splitext(filename)[1].lower()
        mime = "application/octet-stream"
        if ext == ".pdf": mime = "application/pdf"
        elif ext in [".jpg", ".jpeg"]: mime = "image/jpeg"
        elif ext == ".png": mime = "image/png"
        
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            
        doc = Documento(
            filename=filename,
            file_data=file_bytes,
            file_size=size,
            mime_type=mime
        )
        session.add(doc)
        session.flush()
        return doc.id

    @safe_transaction
    def get_document(self, doc_id: int, session=None):
        """Returns tuple (file_data, filename, mime_type)"""
        from models.entities import Documento
        doc = session.query(Documento).get(doc_id)
        if doc:
            return doc.file_data, doc.filename, doc.mime_type
        return None, None, None

    @safe_transaction
    def update(self, id: int, dto: VencimientoUpdateDTO, session=None) -> Vencimiento:
        repo = self._get_repo(session)
        venc = repo.get_with_relations(id)
        if not venc:
            raise ServiceError(f"Vencimiento {id} no encontrado")

        if dto.monto_original is not None:
            venc.monto_original = dto.monto_original
        
        if dto.fecha_vencimiento is not None:
            venc.fecha_vencimiento = dto.fecha_vencimiento
            # Sync Period ONLY if manual period not provided
            if not dto.periodo:
                venc.periodo = f"{dto.fecha_vencimiento.year}-{dto.fecha_vencimiento.month:02d}"
                
        if dto.periodo is not None:
             venc.periodo = dto.periodo

        if dto.obligacion_id is not None:
            venc.obligacion_id = dto.obligacion_id

        if dto.estado_enum is not None:
            venc.estado = dto.estado_enum
            # Gamification Logic
            if venc.estado == EstadoVencimiento.PAGADO:
                self.audio.play_success()
                self._ensure_payment_record(venc, session, dto.monto_pagado, dto.fecha_pago)
        elif dto.estado is not None:
            # Fallback if string passed
            for e in EstadoVencimiento:
                if e.value == dto.estado:
                    venc.estado = e
                    if e == EstadoVencimiento.PAGADO: 
                        self.audio.play_success()
                        self._ensure_payment_record(venc, session, dto.monto_pagado, dto.fecha_pago)
                    break

        if dto.documento_id is not None:
             venc.documento_id = dto.documento_id

        if dto.comprobante_pago_id is not None:
             venc.comprobante_pago_id = dto.comprobante_pago_id

        # Handle File Upload (Start with Legacy, then optional Cloud sync if needed)
        # Note: Controller initiates upload_document separately and passes ID now.
        # But for backward compatibility we keep path logic for local files.
        if dto.new_file_path and not dto.documento_id:
            new_path = self._save_pdf_structured(
                dto.new_file_path,
                venc.periodo,
                venc.obligacion.inmueble.alias,
                venc.obligacion.proveedor.nombre_entidad,
                "FACTURA"
            )
            if new_path:
                venc.ruta_archivo_pdf = new_path

        if dto.new_payment_path and not dto.comprobante_pago_id:
            new_pay_path = self._save_pdf_structured(
                dto.new_payment_path,
                venc.periodo,
                venc.obligacion.inmueble.alias,
                venc.obligacion.proveedor.nombre_entidad,
                "PAGO"
            )
            if new_pay_path:
                venc.ruta_comprobante_pago = new_pay_path

        # Previously repo.update(venc) which uses merge().
        # Since venc is attached and modified, we just need to ensure it's in session (it is)
        # and let commit() handle it. merge() on attached objects can be problematic if state is mixed.
        repo.update(venc)
        return venc

    @safe_transaction
    def delete_document(self, id: int, doc_type: str, delete_from_disk: bool = False, session=None) -> bool:
        repo = self._get_repo(session)
        venc = repo.get_by_id(id)
        if not venc:
            return False
        
        file_path = None
        if doc_type == "invoice":
            file_path = venc.ruta_archivo_pdf
        elif doc_type == "payment":
            file_path = venc.ruta_comprobante_pago
            
        if not file_path:
            return False
            
        if delete_from_disk:
            full_path = DOCS_DIR / file_path
            if full_path.exists():
                os.remove(full_path)
        
        # Clear field
        if doc_type == "invoice":
            venc.ruta_archivo_pdf = None
        elif doc_type == "payment":
            venc.ruta_comprobante_pago = None
            
        repo.update(venc)
        return True

    @safe_transaction
    def soft_delete(self, id: int, session=None) -> bool:
        """Sets is_deleted=1 instead of removing row."""
        repo = self._get_repo(session)
        venc = repo.get_by_id(id)
        if not venc: return False
        
        venc.is_deleted = 1
        repo.update(venc)
        return True

    @safe_transaction
    def delete(self, id: int, session=None) -> bool:
        """Hard delete of Vencimiento."""
        repo = self._get_repo(session)
        return repo.delete(id)

    def _save_pdf_structured(self, src_path, periodo_str, inmueble_alias, servicio_nombre, doc_type="FACTURA"):
        try:
            mes, anio = periodo_str.split('-')
            
            def sanitize(name):
                return "".join([c for c in name if c.isalnum() or c in (' ', '_', '-')]).strip()

            safe_inm = sanitize(inmueble_alias)
            safe_serv = sanitize(servicio_nombre)
            
            target_dir = DOCS_DIR / anio / mes / safe_inm
            target_dir.mkdir(parents=True, exist_ok=True)
            
            ext = os.path.splitext(src_path)[1].lower()
            # Include Doc Type in filename
            new_name = f"{anio}-{mes}_{safe_serv}_{safe_inm}_{doc_type}{ext}"
            dst = target_dir / new_name
            
            if dst.exists():
                from uuid import uuid4
                new_name = f"{anio}-{mes}_{safe_serv}_{safe_inm}_{doc_type}_{uuid4().hex[:4]}{ext}"
                dst = target_dir / new_name

            shutil.copy2(src_path, dst)
            return str(dst.relative_to(DOCS_DIR))
        except Exception as e:
            app_logger.error(f"Error guardando PDF: {e}")
            return None

    def _ensure_payment_record(self, vencimiento, session, monto_pagado=None, fecha_pago=None):
        """Creates or Updates a Pago record."""
        # Defaults
        if monto_pagado is None: monto_pagado = vencimiento.monto_original
        if fecha_pago is None: fecha_pago = date.today()
        
        # Ensure float
        try:
             monto_pagado = float(monto_pagado)
        except:
             pass

        app_logger.info(f"Payment Record Update: VencID={vencimiento.id}, Monto={monto_pagado}, Fecha={fecha_pago}")

        if vencimiento.pagos:
            # Update existing (Assume single payment for now)
            pago = vencimiento.pagos[0]
            pago.fecha_pago = fecha_pago
            pago.monto = monto_pagado
            # Explicitly attach to session to ensure update is tracked (since venc might be detached)
            session.add(pago)
            # Preserve path if not set elsewhere? It is separate column in Vencimiento currently, 
            # but Pago has it too. Sync if needed.
        else:
            pago = Pago(
                vencimiento_id=vencimiento.id,
                fecha_pago=fecha_pago,
                monto=monto_pagado,
                medio_pago="Detectado Automático", 
                comprobante_path=vencimiento.ruta_comprobante_pago
            )
            session.add(pago)
            app_logger.info(f"Payment recorded for Vencimiento {vencimiento.id}: {monto_pagado} on {fecha_pago}")


    @safe_transaction
    def clone_period(self, source_period: str, target_period: str, session=None) -> int:
        """
        Clones all non-deleted vencimientos from source_period to target_period.
        Adjusts due dates to the new month.
        Returns the number of cloned records.
        """
        repo = self._get_repo(session)
        
        # 1. Fetch Source Records
        sources = session.query(Vencimiento).filter(
            Vencimiento.periodo == source_period,
            Vencimiento.is_deleted == 0
        ).all()
        
        if not sources:
            return 0
            
        count = 0
        # Parse target period "YYYY-MM"
        try:
            t_year, t_month = map(int, target_period.split('-'))
        except ValueError:
            raise ServiceError(f"Formato de período destino inválido: {target_period}")
            
        import calendar
        
        for src in sources:
            # Check if already exists in target (Obligacion + Period)
            exists = session.query(Vencimiento).filter(
                Vencimiento.obligacion_id == src.obligacion_id,
                Vencimiento.periodo == target_period,
                Vencimiento.is_deleted == 0
            ).first()
            
            if exists:
                continue # Skip duplicates
                
            # Calculate new date
            # Try to keep same day. If day > max_days_in_new_month, clamp it.
            old_day = src.fecha_vencimiento.day
            _, max_days = calendar.monthrange(t_year, t_month)
            new_day = min(old_day, max_days)
            new_date = date(t_year, t_month, new_day)
            
            new_venc = Vencimiento(
                obligacion_id=src.obligacion_id,
                periodo=target_period,
                fecha_vencimiento=new_date,
                monto_original=src.monto_original,
                estado=EstadoVencimiento.PENDIENTE,
                ruta_archivo_pdf=None,
                ruta_comprobante_pago=None,
                # observaciones=src.observaciones
            )
            session.add(new_venc)
            count += 1
            
        return count

    @safe_transaction
    def get_upcoming(self, days=7, session=None) -> List[Vencimiento]:
        """Returns pending vencimientos due in the next N days."""
        from datetime import timedelta
        repo = self._get_repo(session)
        today = date.today()
        limit_date = today + timedelta(days=days)
        
        # Custom query with Eager Loading + Expunge
        from sqlalchemy.orm import joinedload
        results = session.query(Vencimiento).options(
            joinedload(Vencimiento.obligacion).joinedload(Obligacion.inmueble),
            joinedload(Vencimiento.obligacion).joinedload(Obligacion.proveedor)
        ).join(Vencimiento.obligacion).filter(
            Vencimiento.is_deleted == 0,
            Vencimiento.estado == EstadoVencimiento.PENDIENTE,
            Vencimiento.fecha_vencimiento >= today,
            Vencimiento.fecha_vencimiento <= limit_date
        ).order_by(Vencimiento.fecha_vencimiento.asc()).all()
        
        # Expunge to detach from session
        for r in results:
            session.expunge(r)
            
        return results
