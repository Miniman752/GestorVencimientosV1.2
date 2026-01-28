from datetime import date, datetime
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from database import SessionLocal
from models.entities import Pago, Vencimiento, Obligacion, ProveedorServicio, Inmueble, Moneda
from utils.decorators import safe_transaction
from utils.logger import app_logger

class TreasuryService:
    @staticmethod
    @safe_transaction
    def get_movements(
        start_date: date, 
        end_date: date, 
        inmueble_id: Optional[int] = None, 
        proveedor_id: Optional[int] = None, 
        periodo_id: Optional[str] = None,
        session=None
    ) -> List[dict]:
        """
        Fetches payments with filters.
        """
        # Eager load
        query = session.query(Pago).join(Pago.vencimiento).join(Vencimiento.obligacion)\
            .options(
                joinedload(Pago.vencimiento).joinedload(Vencimiento.obligacion).joinedload(Obligacion.proveedor),
                joinedload(Pago.vencimiento).joinedload(Vencimiento.obligacion).joinedload(Obligacion.inmueble)
            )
            
        # 1. Base Date Filter (unless Period override?)
        # Let's trust caller: if Period is set, caller might set specific dates, or we filter by period string
        if periodo_id and periodo_id != "Todos":
             query = query.filter(Vencimiento.periodo == periodo_id)
        else:
             # Use Date Range
             query = query.filter(Pago.fecha_pago >= start_date, Pago.fecha_pago <= end_date)
             
        # 2. Extra Filters
        if inmueble_id:
             query = query.filter(Obligacion.inmueble_id == inmueble_id)
        
        if proveedor_id:
             query = query.filter(Obligacion.servicio_id == proveedor_id) # servicio_id maps to proveedor table

        # HARD FIX: Filter deleted Vencimientos (Zombies)
        query = query.filter(Vencimiento.is_deleted == 0)

        query = query.order_by(Pago.fecha_pago.desc())

        results = query.all()
        
        from services.forex_service import ForexService
        from models.entities import Moneda
        forex = ForexService()
        
        movements = []
        for p in results:
            venc = p.vencimiento
            obl = venc.obligacion if venc else None
            prov = obl.proveedor if obl else None
            inm = obl.inmueble if obl else None
            
            # Safe access
            entidad_nombre = prov.nombre_entidad if prov else "Desconocido"
            categoria = prov.categoria if prov else "-"
            inmueble_alias = inm.alias if inm else "-"
            
            # Determine Currency
            moneda_key = "ARS"
            if venc and venc.moneda:
                moneda_key = venc.moneda.value if hasattr(venc.moneda, "value") else str(venc.moneda)
            
            # Calculate USD Equivalent
            monto_usd = 0.0
            k = str(moneda_key).upper()
            if "USD" in k or "DOLAR" in k:
                monto_usd = p.monto
            else:
                try:
                    # Convert
                    monto_usd = forex.convert(p.monto, Moneda.ARS, Moneda.USD, p.fecha_pago, session)
                except:
                    pass

            item = {
                "id": p.id,
                "fecha": p.fecha_pago,
                "tipo": "EGRESO", 
                "categoria": categoria,
                "entidad": entidad_nombre,
                "concepto": inmueble_alias,
                "monto": p.monto,
                "monto_usd": monto_usd, # New Field
                "moneda": moneda_key,
                "medio_pago": p.medio_pago or "Otro",
                "comprobante_id": p.documento_id or p.comprobante_path
            }
                
            movements.append(item)
            
        return movements

    @staticmethod
    @safe_transaction
    def get_summary(
        start_date: date, 
        end_date: date, 
        inmueble_id: Optional[int] = None, 
        proveedor_id: Optional[int] = None, 
        periodo_id: Optional[str] = None,
        session=None
    ) -> dict:
        """
        Returns KPI totals for the period.
        """
        movements = TreasuryService.get_movements(
            start_date, end_date, inmueble_id, proveedor_id, periodo_id, session=session
        )
        
        from services.forex_service import ForexService
        from models.entities import Moneda
        
        forex = ForexService()
        
        count = len(movements)
        totals_by_currency = {}
        total_usd_equivalent = 0.0
        
        # Optimization: limit repeated queries? 
        # For now, let's just loop. Session is active.
        
        for m in movements:
            curr = m["moneda"]
            val = m["monto"]
            fecha = m["fecha"]
            
            # 1. Nominal Sum
            totals_by_currency[curr] = totals_by_currency.get(curr, 0.0) + val
            
            # 2. USD Equivalent
            # Check if it looks like USD
            k = str(curr).upper()
            if "USD" in k or "DOLAR" in k or "DÓLAR" in k:
                total_usd_equivalent += val
            else:
                # Assume ARS or convert attempts
                # Try conversion
                try:
                    # We need Moneda Enum
                    # Assuming basic ARS input if not USD
                    converted = forex.convert(val, Moneda.ARS, Moneda.USD, fecha, session)
                    total_usd_equivalent += converted
                except Exception as e:
                    # Fallback or log?
                    print(f"Conversion error for {val} on {fecha}: {e}")
                    pass
            
        return {
            "count": count,
            "totals": totals_by_currency,
            "total_usd_equivalent": total_usd_equivalent
        }
