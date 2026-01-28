from typing import List, Optional
from models.entities import Vencimiento, EstadoVencimiento
from services.vencimiento_service import VencimientoService
from services.period_service import PeriodService
from dtos.vencimiento import VencimientoCreateDTO, VencimientoUpdateDTO
from utils.logger import app_logger
import os
import platform
from config import DOCS_DIR, FILTER_ALL_OPTION

from datetime import date
from services.forex_service import ForexService
from services.audio_service import AudioService
from database import SessionLocal

class VencimientosController:
    def __init__(self):
        self.service = VencimientoService()
        self.audio = AudioService()
        self.forex_service = ForexService()

    def get_usd_rate(self) -> float:
        """Returns current BLUE sell rate or 1.0 if not available."""
        # Use simple session management for this read-only op
        session = SessionLocal()
        try:
            return self.forex_service.get_rate(date.today(), session)
        finally:
            session.close()

    def get_upcoming_alerts(self, days=7) -> List[Vencimiento]:
        return self.service.get_upcoming(days=days)

    def get_all_vencimientos(self, inmueble_id=None, estado=None, period_id=None, page=1, limit=50) -> tuple[List[Vencimiento], int]:
        # Maps "Todos" to None for service layer
        f_inm = None if inmueble_id == FILTER_ALL_OPTION else inmueble_id
        f_est = None if estado == FILTER_ALL_OPTION else estado
        
        # Inject is_deleted filter via kwarg if supported, or via Service modification
        # Since we modified Service signature in Phase 14, let's check Service.
        # Best way: Update Service/Repository to default filter is_deleted=0.
        # Let's do it in Repository. For now, just pass args.
        
        offset = (page - 1) * limit
        return self.service.get_all(inmueble_id=f_inm, estado=f_est, period_id=period_id, limit=limit, offset=offset)

    def get_vencimiento_details(self, vencimiento_id: int) -> Optional[Vencimiento]:
        """Get full vencimiento with relations (for editing)."""
        return self.service.get_with_relations(vencimiento_id)

    # ... (create/update remain same) ...

    def delete_vencimiento(self, vencimiento_id: int) -> bool:
        # Check Period Lock
        try:
            current_venc = self.service.get_by_id(vencimiento_id)
            if current_venc:
                PeriodService.check_period_status(current_venc.fecha_vencimiento)
            
            # Soft Delete
            self.service.soft_delete(vencimiento_id) 
            self.audio.play_success() # "Trash Sound"
            return True
        except Exception as e:
            app_logger.error(f"Controller Error Delete Document: {e}")
            self.audio.play_error()
            raise e

    def create_vencimiento(self, data: dict) -> bool:
        try:
            # Period Guard
            PeriodService.check_period_status(data.get('fecha_vencimiento'))

            # Map dict to DTO
            # Default to YYYY-MM standard from date if period is missing or non-standard
            # This fixes "disconnected cables" where user types MM-YYYY but system expects YYYY-MM
            fecha = data['fecha_vencimiento']
            periodo_std = f"{fecha.year}-{fecha.month:02d}"
            
            dto = VencimientoCreateDTO(
                obligacion_id=data['obligacion_id'],
                periodo=periodo_std, # Enforce Standard (Ignore UI text if needed, or validate it matches)
                fecha_vencimiento=data['fecha_vencimiento'],
                monto_original=data['monto_original'],
                estado=data['estado'],
                ruta_archivo_pdf=data.get('ruta_archivo_pdf'),
                ruta_comprobante_pago=data.get('ruta_comprobante_pago')
            )
            
            # Cloud Upload (Create)
            if data.get('ruta_archivo_pdf'):
                try:
                    doc_id = self.service.upload_document(data['ruta_archivo_pdf'])
                    dto.documento_id = doc_id
                except Exception as ex:
                    app_logger.warning(f"Failed to upload document on create: {ex}")

            if data.get('ruta_comprobante_pago'):
                try:
                    doc_id = self.service.upload_document(data['ruta_comprobante_pago'])
                    dto.comprobante_pago_id = doc_id
                except Exception as ex:
                    app_logger.warning(f"Failed to upload payment doc on create: {ex}")

            self.service.create(dto)
            self.audio.play_success()
            return True
        except Exception as e:
            app_logger.error(f"Controller Error Create: {e}")
            self.audio.play_error()
            raise e 

    def update_vencimiento(self, vencimiento_id: int, data: dict) -> bool:
        try:
            # 1. Check Existing Record (Origin Period)
            current_venc = self.service.get_by_id(vencimiento_id)
            if current_venc:
                PeriodService.check_period_status(current_venc.fecha_vencimiento)

            # 2. Check New Date (Target Period)
            if data.get('fecha_vencimiento'):
                 PeriodService.check_period_status(data.get('fecha_vencimiento'))

            dto = VencimientoUpdateDTO(
                monto_original=data.get('monto_original'),
                fecha_vencimiento=data.get('fecha_vencimiento'),
                obligacion_id=data.get('obligacion_id'), # Added line

                # Robust Enum Conversion
                estado_enum=None,
                estado=None,
                new_file_path=data.get('new_file_path'),
                new_payment_path=data.get('new_payment_path'),
                monto_pagado=data.get('monto_pagado'),
                fecha_pago=data.get('fecha_pago'),
                
                # Cloud IDs
                documento_id=data.get('documento_id'),
                comprobante_pago_id=data.get('comprobante_pago_id')
            )
            
            # Cloud Upload (Update)
            if data.get('new_file_path'):
                 try:
                     doc_id = self.service.upload_document(data['new_file_path'])
                     dto.documento_id = doc_id
                     # Clear path in DTO so service doesn't try to copy local file?
                     # Service logic checks: if new_file_path and not documento_id.
                     # So if we set documento_id, it skips local copy logic if we want.
                     # But we might want both (Hybrid). Service handles it.
                 except Exception as ex:
                     app_logger.error(f"Upload error: {ex}")

            if data.get('new_payment_path'):
                 try:
                     doc_id = self.service.upload_document(data['new_payment_path'])
                     dto.comprobante_pago_id = doc_id
                 except Exception as ex:
                     app_logger.error(f"Upload error: {ex}")
            
            # Helper to parse state
            raw_state = data.get('estado')
            if isinstance(raw_state, EstadoVencimiento):
                dto.estado_enum = raw_state
                dto.estado = raw_state.value
            elif isinstance(raw_state, str):
                # Try Key (PAGADO)
                if raw_state.upper() in EstadoVencimiento.__members__:
                     dto.estado_enum = EstadoVencimiento[raw_state.upper()]
                # Try Value ("Pagado")
                else:
                    for e in EstadoVencimiento:
                        if e.value == raw_state:
                            dto.estado_enum = e
                            break
                if dto.estado_enum:
                    dto.estado = dto.estado_enum.value
            
            app_logger.info(f"Update Vencimiento {vencimiento_id}: Status Raw='{raw_state}'Parsed='{dto.estado_enum}'")
            self.service.update(vencimiento_id, dto)
            self.audio.play_success()
            return True
        except Exception as e:
            app_logger.error(f"Controller Error Update: {e}")
            self.audio.play_error()
            raise e

    def delete_document(self, vencimiento_id: int, doc_type="invoice", delete_file_from_disk=False) -> bool:
        # Check Period Lock
        try:
            current_venc = self.service.get_by_id(vencimiento_id)
            if current_venc:
                PeriodService.check_period_status(current_venc.fecha_vencimiento)
            return self.service.delete_document(vencimiento_id, doc_type, delete_file_from_disk)
        except Exception as e:
            app_logger.error(f"Controller Error Delete Document: {e}")
            raise e

    def open_document_unified(self, vencimiento_id: int, doc_type="invoice"):
        """
        Opens document. Prioritizes:
        1. Cloud Blob (if exists) -> Save to Temp -> Open
        2. Local File (Legacy path)
        """
        try:
            venc = self.service.get_by_id(vencimiento_id)
            if not venc: return False
            
            # Determine correct ID and Path
            doc_id = None
            filename = None
            
            if doc_type == "invoice":
                doc_id = venc.documento_id
                filename = venc.ruta_archivo_pdf
            elif doc_type == "payment":
                doc_id = venc.comprobante_pago_id
                filename = venc.ruta_comprobante_pago
            
            # 1. Try Cloud Fetch
            if doc_id:
                file_data, name, mime = self.service.get_document(doc_id)
                if file_data:
                     import tempfile
                     # Create temp file with correct extension
                     ext = os.path.splitext(name)[1] if name else ".pdf"
                     prefix = f"TEMP_{vencimiento_id}_{doc_type}_"
                     
                     with tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix=prefix) as tmp:
                         tmp.write(file_data)
                         tmp_path = tmp.name
                         
                     # Open it
                     if platform.system() == 'Windows':
                        os.startfile(tmp_path)
                     else:
                        import subprocess
                        subprocess.call(('xdg-open', tmp_path))
                     return True

            # 2. Try Local Legacy
            return self.open_pdf(filename)

        except Exception as e:
            app_logger.error(f"Error opening document unified: {e}")
            return False

    def open_pdf(self, filename):
        """Legacy Helper for UI to open PDF from DOCS_DIR."""
        if not filename: return False
        
        try:
            filepath = DOCS_DIR / filename
            if filepath.exists():
                if platform.system() == 'Windows':
                    os.startfile(filepath)
                else:
                    import subprocess
                    subprocess.call(('xdg-open', str(filepath)))
                return True
            else:
                app_logger.warning(f"File not found: {filepath}")
                return False
        except Exception as e:
            app_logger.error(f"Error opening PDF: {e}")
            return False

    def preview_csv(self, file_path):
        """Reads first rows for preview (Delegated to Helper)."""
        try:
            from utils.import_helper import load_data_file
            df = load_data_file(file_path, header_row=0) 
            return True, df.head(5)
        except Exception as e:
            return False, str(e)

    def process_import(self, file_path, mapping_dict):
        """
        Imports Vencimientos from DataFrame via Service.
        """
        try:
            from utils.import_helper import load_data_file
            df = load_data_file(file_path)
            
            # Delegate to Service
            success_count, errors = self.service.import_from_dataframe(df, mapping_dict)
            
            if errors:
                return True, f"Importado con Advertencias:\n{success_count} filas ok.\nErrores:\n" + "\n".join(errors[:5])
            else:
                return True, f"Importación Exitosa: {success_count} registros creados."

        except Exception as e:
            app_logger.error(f"Import failed: {e}")
            return False, str(e)



    def get_document_bytes(self, documento_id):
        """Proxi to service."""
        try:
            return self.service.get_document(documento_id)
        except Exception as e:
            app_logger.error(f"Error fetching document: {e}")
            return None, None, None
