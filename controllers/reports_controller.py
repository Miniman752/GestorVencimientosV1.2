from services.report_service import ReportService
from utils.logger import app_logger
from utils.import_helper import format_currency
import os
import pandas as pd
from datetime import datetime

class ReportsController:
    def __init__(self):
        self.service = ReportService()

    def export_excel(self, vencimientos, filename="export_vencimientos.xlsx"):
        try:
            # Transform objects to dict list
            data = []
            for v in vencimientos:
                data.append({
                    "Fecha": v.fecha_vencimiento,
                    "Inmueble": v.obligacion.inmueble.alias if v.obligacion and v.obligacion.inmueble else "-",
                    "Servicio": v.obligacion.proveedor.nombre_entidad if v.obligacion and v.obligacion.proveedor else "-",
                    "Monto": v.monto_original,
                    "Estado": v.estado
                })
            
            df = pd.DataFrame(data)
            
            # Ensure folder exists
            out_path = os.path.abspath(filename)
            df.to_excel(out_path, index=False)
            
            return out_path
        except Exception as e:
            app_logger.error(f"Error Export Excel: {e}")
            raise e

    def export_pdf_report(self, vencimientos, filename="reporte_deuda.pdf"):
        try:
            # 1. Prepare Data
            headers = ["Fecha", "Inmueble", "Concepto/Prov.", "Monto", "Estado"]
            data_rows = []
            
            total = 0
            
            for v in vencimientos:
                date_str = v.fecha_vencimiento.strftime("%d/%m/%Y") if hasattr(v.fecha_vencimiento, 'strftime') else str(v.fecha_vencimiento)
                inm = v.obligacion.inmueble.alias if (v.obligacion and v.obligacion.inmueble) else "-"
                prov = v.obligacion.proveedor.nombre_entidad if (v.obligacion and v.obligacion.proveedor) else (v.obligacion.servicio_nombre_fake or "?")
                monto = format_currency(v.monto_original)
                estado = v.estado
                
                data_rows.append([date_str, inm, prov, f"$ {monto}", estado])
                
                try: total += float(v.monto_original)
                except: pass
                
            summary = f"Total Deuda/Vencimientos: $ {format_currency(total)}"
            
            # 2. Call Service
            out_path = os.path.abspath(filename)
            success, msg = self.service.generate_pdf(
                filename=out_path,
                title="Reporte de Vencimientos",
                headers=headers,
                data_rows=data_rows,
                summary_text=summary
            )
            
            if not success:
                raise Exception(msg)
                
            return out_path
            
        except Exception as e:
            app_logger.error(f"Error Export PDF: {e}")
            raise e

    def export_treasury_pdf(self, movements, filename="reporte_caja.pdf"):
        try:
            # 1. Prepare Data
            # Columns: Fecha, Tipo, Categoría, Entidad, Concepto, Monto
            # Alignments: L, L, L, L, L, R
            headers = ["Fecha", "Tipo", "Categoría", "Entidad", "Concepto", "Monto"]
            col_aligns = ["LEFT", "CENTER", "LEFT", "LEFT", "LEFT", "RIGHT"]
            
            data_rows = []
            total_egreso = 0
            
            for m in movements:
                d = m.get("fecha")
                date_str = d.strftime("%d/%m/%Y") if d else ""
                tipo = m.get("tipo", "")
                cat = m.get("categoria", "")
                ent = m.get("entidad", "")
                conc = m.get("concepto", "")
                
                # Format Amount
                mon = m.get("moneda", "$")
                raw = m.get("monto", 0)
                monto_str = f"{mon} {format_currency(raw)}"
                
                # Add to rows
                data_rows.append([date_str, tipo, cat, ent, conc, monto_str])
                
                try: total_egreso += float(raw)
                except: pass
                
            summary = f"Total Egresos del Período: $ {format_currency(total_egreso)}"
            
            # 2. Call Service
            out_path = os.path.abspath(filename)
            success, msg = self.service.generate_pdf(
                filename=out_path,
                title="Reporte Profesional de Tesorería",
                headers=headers,
                data_rows=data_rows,
                summary_text=summary,
                col_alignments=col_aligns
            )
            
            if not success:
                raise Exception(msg)
                
            return out_path
            
        except Exception as e:
            app_logger.error(f"Error Export Treasury PDF: {e}")
            raise e


