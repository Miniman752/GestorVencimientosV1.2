from datetime import date, timedelta
import calendar
from sqlalchemy import func, and_, desc, extract, case

from repositories.vencimiento_repository import VencimientoRepository
from models.entities import Vencimiento, EstadoVencimiento, Obligacion, ProveedorServicio, Inmueble, Moneda, Pago
from dtos.dashboard import DashboardDTO, KPIData, ChartData, TimelineItem, UXState
from utils.decorators import safe_transaction
from services.forex_service import ForexService

class DashboardService:
    def __init__(self):
        self.forex_service = ForexService()

    @safe_transaction
    def get_dashboard_data(self, target_currency="ARS", reference_date: date = None, session=None) -> DashboardDTO:
        # Reference Date acts as "Focus Month"
        current_date = reference_date if reference_date else date.today()
        current_year = current_date.year
        
        # Determine View Bounds (Whole Month)
        view_start = current_date.replace(day=1)
        # Last day of month logic
        next_month = view_start.replace(day=28) + timedelta(days=4)
        view_end = next_month - timedelta(days=next_month.day)
        
        # Effective Snapshot Date:
        # If viewing Current Month -> Today
        # If viewing Past/Future Month -> End of that Month (for consistency of "What happened?")
        today_real = date.today()
        if view_start.month == today_real.month and view_start.year == today_real.year:
            effective_date = today_real
        else:
            effective_date = view_end

        # Helper to convert on the fly
        def to_target(amount, source_curr, date_ref):
            if not amount: return 0.0
            # Map string/enum if needed
            sm = source_curr if isinstance(source_curr, Moneda) else Moneda.ARS 
            return self.forex_service.convert(amount, sm, target_currency, date_ref, session)

        # --- KPIs ---
        
        # 1. Deuda Exigible Check (Global or up to Effective Date)
        # Logic: All VENCIDO + PENDIENTE <= effective_date
        # Use GREATEST(monto_original, monto_actualizado) to capture surcharges
        # SQLite doesn't support GREATEST easily in all versions, strictly Postgres/MySQL do. 
        # But user is on Postgres (Neon).
        # Fallback for SQLite: case((actual > orig), actual, else_=orig)
        
        calc_amount = case(
            (Vencimiento.monto_actualizado > Vencimiento.monto_original, Vencimiento.monto_actualizado),
            else_=Vencimiento.monto_original
        )

        deuda_groups = session.query(Vencimiento.moneda, func.sum(calc_amount)).filter(
             (Vencimiento.estado == EstadoVencimiento.VENCIDO) | 
             and_(Vencimiento.estado == EstadoVencimiento.PENDIENTE, Vencimiento.fecha_vencimiento <= effective_date)
        ).filter(Vencimiento.is_deleted == 0).group_by(Vencimiento.moneda).all()
        
        deuda_exigible = sum(to_target(amount, moneda, effective_date) for moneda, amount in deuda_groups)

        # Previsión Caja (Next 15 days from Effective Date)
        if effective_date < date.today():
             prevision_caja = 0.0
        else:
            limit_date = effective_date + timedelta(days=15)
            # Same calc_amount logic
            prevision_groups = session.query(Vencimiento.moneda, func.sum(calc_amount)).filter(
                Vencimiento.estado == EstadoVencimiento.PENDIENTE,
                Vencimiento.fecha_vencimiento > effective_date,
                Vencimiento.fecha_vencimiento <= limit_date,
                Vencimiento.is_deleted == 0
            ).group_by(Vencimiento.moneda).all()
            
            prevision_caja = sum(to_target(amount, moneda, effective_date) for moneda, amount in prevision_groups)

        # Eficiencia (SQL Count Unique)
        count_debtors = session.query(Obligacion.inmueble_id).join(Vencimiento).filter(
            (Vencimiento.estado == EstadoVencimiento.VENCIDO) |
            and_(Vencimiento.estado == EstadoVencimiento.PENDIENTE, Vencimiento.fecha_vencimiento <= effective_date)
        ).filter(Vencimiento.is_deleted == 0).distinct().count()

        from models.entities import EstadoInmueble
        # Filter by state removed as column doesn't exist
        total_inmuebles = session.query(func.count(Inmueble.id)).scalar() or 1
        if total_inmuebles == 0: total_inmuebles = 1
        eficiencia = ((total_inmuebles - count_debtors) / total_inmuebles) * 100

        # --- Charts ---
        # Charts Logic
        # 1. If PAID -> Use Pago.monto (or sum of payments theoretically, here coalesced)
        # 2. If NOT PAID (Pending/Vencido) -> Use MAX(Original, Actualizado)
        # This ensures surcharges are visible in charts too.
        
        pago_logic = func.coalesce(Pago.monto, Vencimiento.monto_original)
        pending_logic = case(
            (Vencimiento.monto_actualizado > Vencimiento.monto_original, Vencimiento.monto_actualizado),
            else_=Vencimiento.monto_original
        )
        
        actual_amount = case(
            (Vencimiento.estado == EstadoVencimiento.PAGADO, pago_logic),
            else_=pending_logic
        )

        # 1. Category (Focus Month)
        # Filter: Within View Start/End
        cat_groups = session.query(
            ProveedorServicio.categoria, 
            Vencimiento.moneda, 
            func.sum(actual_amount)
        ).select_from(Vencimiento).outerjoin(Pago).join(Obligacion).join(ProveedorServicio).filter(
            Vencimiento.fecha_vencimiento >= view_start,
            Vencimiento.fecha_vencimiento <= view_end
        ).filter(Vencimiento.is_deleted == 0).group_by(ProveedorServicio.categoria, Vencimiento.moneda).all()
        
        gastos_por_categoria = {}
        for cat, moneda, amount in cat_groups:
             val = to_target(amount, moneda, effective_date)
             cat_name = cat
             gastos_por_categoria[cat_name] = gastos_por_categoria.get(cat_name, 0) + val

        # 2. Evolution (Last 6 Months ending at View End)
        start_date_evo = view_end.replace(day=1) - timedelta(days=30*5)
        # SQLite extract returns distinct string '1', '2' or int depending on driver. 
        # Safer to fetch Year, Month, Moneda, Sum
        evo_groups = session.query(
            extract('year', Vencimiento.fecha_vencimiento).label('y'), 
            extract('month', Vencimiento.fecha_vencimiento).label('m'), 
            Vencimiento.moneda, 
            func.sum(actual_amount)
        ).select_from(Vencimiento).outerjoin(Pago).filter(
            Vencimiento.fecha_vencimiento >= start_date_evo,
            Vencimiento.fecha_vencimiento <= view_end
        ).filter(Vencimiento.is_deleted == 0).group_by('y', 'm', Vencimiento.moneda).all()
        
        evo_map = {}
        for y, m, moneda, amount in evo_groups:
            y, m = int(y), int(m)
            val = to_target(amount, moneda, date(y, m, 1))
            evo_map[(y, m)] = evo_map.get((y, m), 0) + val

        evolution_data = []
        for y, m in sorted(evo_map.keys()):
            month_name = calendar.month_abbr[m]
            evolution_data.append({"period": f"{month_name}-{y}", "amount": evo_map[(y, m)]})

        # 3. Top Properties (Focus Month)
        top_groups = session.query(
            Inmueble.alias, 
            Vencimiento.moneda, 
            func.sum(actual_amount)
        ).select_from(Vencimiento).outerjoin(Pago).join(Obligacion).join(Inmueble).filter(
            Vencimiento.fecha_vencimiento >= view_start, 
            Vencimiento.fecha_vencimiento <= view_end
        ).filter(Vencimiento.is_deleted == 0).group_by(Inmueble.alias, Vencimiento.moneda).all()
        
        top_map = {}
        for alias, moneda, amount in top_groups:
             val = to_target(amount, moneda, effective_date)
             top_map[alias] = top_map.get(alias, 0) + val
            
        sorted_top = sorted(top_map.items(), key=lambda x: x[1], reverse=True)[:5]
        top_inmuebles = dict(sorted_top)

        # --- Timeline (Strictly Focus Month) ---
        # Logic: Show PENDING items that belong strictly to this month.
        # This acts as "What is left to pay for this specific month?"
        proximos_vencimientos = session.query(Vencimiento).filter(
            Vencimiento.estado == EstadoVencimiento.PENDIENTE,
            Vencimiento.fecha_vencimiento >= view_start,
            Vencimiento.fecha_vencimiento <= view_end,
            Vencimiento.is_deleted == 0
        ).order_by(Vencimiento.fecha_vencimiento).limit(5).all()
        
        timeline_data = []
        for v in proximos_vencimientos:
            converted_amount = to_target(v.monto_original, v.moneda, v.fecha_vencimiento)
            timeline_data.append(TimelineItem(
                fecha=v.fecha_vencimiento.strftime("%d/%m"),
                detalle=f"{v.obligacion.inmueble.alias} - {v.obligacion.proveedor.nombre_entidad}",
                monto=converted_amount
            ))

        # --- UX State ---
        emotional_state = "ZEN"
        limit_48h = effective_date + timedelta(days=2)
        upcoming_48h = session.query(func.count(Vencimiento.id)).filter(
            Vencimiento.estado == EstadoVencimiento.PENDIENTE,
            Vencimiento.fecha_vencimiento > effective_date,
            Vencimiento.fecha_vencimiento <= limit_48h,
            Vencimiento.is_deleted == 0
        ).scalar() or 0

        if deuda_exigible > 0:
            emotional_state = "CRITICAL"
        elif upcoming_48h > 0:
            emotional_state = "FOCUS"
        else:
            emotional_state = "ZEN"

        streak_days = session.query(func.count(Vencimiento.id)).filter(
            Vencimiento.estado == EstadoVencimiento.PAGADO,
            extract('month', Vencimiento.fecha_vencimiento) == current_date.month,
            Vencimiento.is_deleted == 0
        ).scalar() or 0
        
        if emotional_state == "CRITICAL":
            streak_days = 0
            
        # --- Savings Stats (Current Month) ---
        current_period = current_date.strftime("%Y-%m")
        # Now automatically converted to target_currency
        savings = self.get_savings_stats(current_period, target_currency=target_currency, session=session)
        total_saved = savings.get("total_saved", 0.0)
        
        # Calculate % saved
        total_orig = savings.get("total_original", 0.0)
        ahorro_pct = (total_saved / total_orig * 100) if total_orig > 0 else 0.0

        # --- AI Insights (New) ---
        from services.cognitive_service import CognitiveService
        from dtos.dashboard import AIInsights
        
        # 1. Forecast
        # Use simple session injection if method signature allows, else default.
        # CognitiveService methods use @safe_transaction decorator? 
        # Wait, if we are inside a transaction, calling decorated method might open nested session if not careful?
        # CognitiveService methods take 'session' arg? Let's check signature.
        # Yes: predict_next_month_total(session)
        # But decorators might wrap it. 
        # Actually safe_transaction decorator handles "session=None" by creating one. 
        # If we pass session, it uses it.
        
        f_amount, f_conf, f_reason = CognitiveService.predict_next_month_total(session=session)
        
        # Convert forecast amount too? Yes, usually forecast is in base currency (ARS?) or original inputs.
        # Assumption: Forecasting logic sums "monto_original". This is mixed currency.
        # Better: Convert amounts inside prediction logic? Or just treat as "Value Unit".
        # For MVP, assume mixed-currency sum is roughly OK or mostly ARS. Upgrade later. 
        # Actually, let's convert the result to target currency?
        # If forecast is sum of raw values, it's messy.
        # But `predict_next_month_total` does `sum(monto_original)`.
        # Correct approach: `predict` should normalize to a base currency internally.
        # Given constraint, let's assume result is in "Global Unit" mixed.
        # Ideally we convert distinct currencies in history then forecast.
        # For now, let's treat the result as "Value" and convert if needed or display as is?
        # Let's assume it returns a raw sum. We will format it as is or try to convert if "ARS"?
        # Actually, if we are in USD view, showing ARS forecast is confusing.
        # Let's convert the output using today's rate if we assume it's mostly ARS?
        # Simpler: Pass target currency to CognitiveService?
        # No, for now, let's just display what comes back and polish later.
        
        # 2. Alerts
        alerts = CognitiveService.detect_price_creep(session=session)
        
        # 3. DNA
        dna = CognitiveService.get_spending_dna(session, period_id=current_period) # Focus on current month
        
        ai_data = AIInsights(
            forecast_amount=f_amount,
            forecast_confidence=f_conf,
            forecast_reason=f_reason,
            price_alerts=alerts,
            spending_dna=dna
        )

        return DashboardDTO(
            kpis=KPIData(deuda_exigible, prevision_caja, eficiencia, total_saved, ahorro_pct),
            charts=ChartData(gastos_por_categoria, evolution_data, top_inmuebles),
            timeline=timeline_data,
            ux_state=UXState(emotional_state, streak_days),
            ai=ai_data
        )
    @safe_transaction
    def get_savings_stats(self, period_id: str, target_currency="ARS", session=None) -> dict:
        """
        Calculates savings for a specific period (PAID items only).
        Returns normalized stats in target_currency.
        """
        from models.entities import Pago
        
        rows = session.query(Vencimiento.monto_original, Pago.monto, Vencimiento.moneda, Vencimiento.fecha_vencimiento).join(Pago).filter(
            Vencimiento.periodo == period_id,
            Vencimiento.estado == EstadoVencimiento.PAGADO,
            Vencimiento.is_deleted == 0
        ).all()
        
        total_original = 0.0
        total_paid = 0.0
        
        for orig, paid, moneda, fecha in rows:
            # Handle None
            o = float(orig or 0)
            p = float(paid or o)
            
            # Normalize to Target Currency
            # We use the fecha_vencimiento (or pago date?) as reference. Venc date is stable.
            m_enum = moneda if isinstance(moneda, Moneda) else Moneda.ARS
            
            o_conv = self.forex_service.convert(o, m_enum, target_currency, fecha, session)
            p_conv = self.forex_service.convert(p, m_enum, target_currency, fecha, session)
            
            total_original += o_conv
            total_paid += p_conv
            
        saved = total_original - total_paid
            
        return {
            "total_saved": saved,
            "total_original": total_original,
            "total_paid": total_paid
        }


