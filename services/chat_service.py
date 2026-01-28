import re
from sqlalchemy import func
from utils.decorators import safe_transaction
from models.entities import Vencimiento, EstadoVencimiento, ProveedorServicio, Obligacion

class ChatService:
    """
    Interpretation engine for Natural Language Queries (NLP-Lite).
    Translates user questions into SQL queries.
    """
    
    @safe_transaction
    def process_query(self, user_text: str, session=None) -> str:
        import unicodedata
        
        # Normalize: Lowercase + Remove Accents (á -> a)
        text = user_text.lower()
        text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
        
        from datetime import date, datetime
        today = date.today()
        
        # 1. Intent: Total Debt ("cuanto debo", "deuda", "saldo", "pasivo", "rojo", "deficit")
        if any(x in text for x in ["debo", "deuda", "pendiente", "vencido", "saldo", "pasivo", "obligaciones", "tengo que pagar", "rojo", "deficit"]):
            total = session.query(func.sum(Vencimiento.monto_original)).filter(
                Vencimiento.estado.in_([EstadoVencimiento.PENDIENTE, EstadoVencimiento.VENCIDO]),
                Vencimiento.is_deleted == 0
            ).scalar() or 0.0
            
            count = session.query(func.count(Vencimiento.id)).filter(
                Vencimiento.estado.in_([EstadoVencimiento.PENDIENTE, EstadoVencimiento.VENCIDO]),
                Vencimiento.is_deleted == 0
            ).scalar() or 0
            
            if total == 0:
                return "🎉 **¡Estás al día!** No tienes deudas pendientes registradas."
            return f"💰 Tienes una deuda total de **${total:,.2f}** en **{count}** comprobantes pendientes."

        # 2. Intent: Status/Summary of Month ("como vengo", "resumen", "situacion", "balance mes")
        if any(x in text for x in ["como vengo", "resumen", "situacion", "balance", "estado del mes"]):
            current_period = today.strftime("%Y-%m")
            
            # Paid this month (by period)
            paid_val = session.query(func.sum(Vencimiento.monto_original)).filter(
                Vencimiento.periodo == current_period,
                Vencimiento.estado == EstadoVencimiento.PAGADO,
                Vencimiento.is_deleted == 0
            ).scalar()
            paid = float(paid_val or 0)
            
            # Pending this month
            pending_val = session.query(func.sum(Vencimiento.monto_original)).filter(
                Vencimiento.periodo == current_period,
                Vencimiento.estado != EstadoVencimiento.PAGADO,
                Vencimiento.is_deleted == 0
            ).scalar()
            pending = float(pending_val or 0)
            
            pct_paid = 0
            if (paid + pending) > 0:
                pct_paid = int((paid / (paid + pending)) * 100)
                
            return (f"📊 **Resumen Período {current_period}**:\n"
                    f"✅ Pagado: **${paid:,.2f}**\n"
                    f"⏳ Pendiente: **${pending:,.2f}**\n"
                    f"Has cubierto el **{pct_paid}%** de tus obligaciones este mes.")

        # 3. Intent: Highest Expense ("gasto mas alto", "mayor importe", "factura mas cara")
        if any(x in text for x in ["mas alto", "mas caro", "mayor importe", "mas grande", "pico de gasto"]):
            highest = session.query(Vencimiento).filter(
                Vencimiento.is_deleted == 0
            ).order_by(Vencimiento.monto_original.desc()).first()
            
            if highest:
                return f"🏔️ El gasto más alto registrado histórico es de **${highest.monto_original:,.2f}** correspondiente a **{highest.obligacion.proveedor.nombre_entidad}** ({highest.periodo})."
            else:
                return "No tengo datos suficientes."

        # 4. Intent: Last Payment ("ultimo pago", "cuando pague")
        if "ultimo pago" in text or "cuando pague" in text:
            provs = session.query(ProveedorServicio).all()
            for p in provs:
                if p.nombre_entidad.lower() in text:
                    last_pay = session.query(Vencimiento).join(Obligacion).join(ProveedorServicio).filter(
                        ProveedorServicio.id == p.id,
                        Vencimiento.estado == EstadoVencimiento.PAGADO,
                        Vencimiento.is_deleted == 0
                    ).order_by(Vencimiento.fecha_vencimiento.desc()).first()
                    
                    if last_pay:
                        return f"🗓️ El último pago registrado a **{p.nombre_entidad}** fue el **{last_pay.fecha_vencimiento.strftime('%d/%m/%Y')}** por **${last_pay.monto_original:,.2f}**."
                    
            return "No encontré ese proveedor o no tiene pagos. Intenta especificar el nombre (ej: 'último pago Edesur')."

        # 5. Intent: Spending by Provider ("gasto", "pagos", "historial")
        provs = session.query(ProveedorServicio).all()
        for p in provs:
            if p.nombre_entidad.lower() in text:
                total = session.query(func.sum(Vencimiento.monto_original)).join(Obligacion).join(ProveedorServicio).filter(
                    ProveedorServicio.id == p.id,
                    Vencimiento.estado == EstadoVencimiento.PAGADO,
                    Vencimiento.is_deleted == 0
                ).scalar() or 0.0
                return f"🏷️ El histórico total pagado a **{p.nombre_entidad}** es de **${total:,.2f}**."

        # 6. Intent: Next Expirations ("vence", "agenda", "proximo", "cercano", "semana que viene")
        if any(x in text for x in ["vence", "agenda", "proximo", "cercano", "semana que viene"]):
            next_due = session.query(Vencimiento).filter(
                Vencimiento.estado == EstadoVencimiento.PENDIENTE,
                Vencimiento.fecha_vencimiento >= today,
                Vencimiento.is_deleted == 0
            ).order_by(Vencimiento.fecha_vencimiento.asc()).limit(5).all()
            
            if not next_due:
                return "✨ ¡Relax! No tienes vencimientos próximos registrados."
            
            msg = "📅 **Agenda - Próximos Vencimientos:**\n"
            for v in next_due:
                days = (v.fecha_vencimiento - today).days
                msg += f"- {v.fecha_vencimiento.strftime('%d/%m')}: ${v.monto_original:,.2f} ({v.obligacion.proveedor.nombre_entidad}) [En {days} días]\n"
            return msg
            
        # 7. Intent: Count/Stats ("cuantos servicios", "cantidad")
        if any(x in text for x in ["cuantos servicios", "cantidad de facturas", "volumen"]):
             count = session.query(func.count(Vencimiento.id)).filter(Vencimiento.is_deleted==0).scalar()
             active_provs = session.query(func.count(ProveedorServicio.id)).filter(ProveedorServicio.activo==1).scalar()
             return f"🔢 Tienes **{active_provs}** proveedores activos y has procesado un total de **{count}** comprobantes en el sistema."

        # 8. Greeting/Help
        if any(x in text for x in ["hola", "ayuda", "comandos", "que sabes hacer"]):
            return (
                "🤖 **Capacidades Extendidas:**\n"
                "• '¿Cómo vengo este mes?' (Resumen)\n"
                "• '¿Cuál fue mi gasto más alto?'\n"
                "• 'Agenda de vencimientos'\n"
                "• 'Historial de Edesur'\n"
                "• '¿Total en rojo?' (Deuda)"
            )

        return "🤔 Aún estoy aprendiendo. Prueba con 'Resumen', 'Agenda' o 'Deuda'."


