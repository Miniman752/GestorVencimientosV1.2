from statistics import mean, stdev
from typing import Optional
from sqlalchemy import func
from utils.decorators import safe_transaction
from models.entities import Vencimiento, EstadoVencimiento

class CognitiveService:
    """
    Advanced cognitive analysis for anomaly detection and pattern recognition.
    Acts as a proactive brain monitoring data entry.
    """
    
    @staticmethod
    def predict_category(text: str) -> Optional[str]:
        """
        Predicts category based on provider name using keyword clustering.
        Returns the value of CategoriaServicio or None.
        """
        if not text: return None
        text = text.lower().strip()
        
        # Mapping (Clustering)
        keywords = {
            "Impuesto": ["arba", "agip", "afip", "patente", "inmobiliario", "municipal", "rentas", "impuesto", "monotributo"],
            "Expensa": ["expensa", "consorcio", "administracion", "edificio", "torre"],
            "Servicio": ["luz", "gas", "agua", "internet", "fibertel", "telecentro", "personal", "movistar", "claro", "edesur", "edenor", "metrogas", "naturgy", "aysa", "seguro", "netflix", "spotify", "visa", "master", "amex", "tarjeta", "cable"]
        }
        
        for cat, terms in keywords.items():
            for term in terms:
                if term in text:
                    return cat # Matches CategoriaServicio values strings
        
        return None
    @staticmethod
    @safe_transaction
    def detect_anomaly(obligacion_id: int, new_amount: float, session=None) -> tuple[bool, str]:
        """
        Analyzes historical payments for this obligation to detect anomalies.
        Returns: (True/False, Reason Argument)
        """
        if not obligacion_id:
            return False, ""
            
        # 1. Fetch History (Last 6 payments)
        history = session.query(Vencimiento).filter(
            Vencimiento.obligacion_id == obligacion_id,
            Vencimiento.estado == EstadoVencimiento.PAGADO,
            Vencimiento.is_deleted == 0
        ).order_by(Vencimiento.fecha_vencimiento.desc()).limit(6).all()
        
        if len(history) < 3:
            return False, "Insuficiente data histórica"

         # Convert to float for stat calc
        amounts = [float(h.monto_original) for h in history]
        
        # 2. Heuristics
        avg = mean(amounts)
        
        # Threshold: 40% deviation from Moving Average
        threshold = 0.4
        
        # Check High Anomaly
        if new_amount > avg * (1 + threshold):
            pct_diff = int(((new_amount - avg) / avg) * 100)
            return True, f"El monto ingresado (${new_amount:,.2f}) es un {pct_diff}% mayor al promedio histórico (${avg:,.2f}).\n¿Confirma que es correcto?"
            
        # Check Low Anomaly (Suspiciously low)
        if new_amount < avg * (1 - threshold):
             pct_diff = int(((avg - new_amount) / avg) * 100)
             return True, f"El monto ingresado es un {pct_diff}% menor al promedio histórico.\nPosible error de tipeo o factura parcial."

        return False, ""

    @staticmethod
    @safe_transaction
    def check_duplicate(obligacion_id: int, periodo: str, session=None) -> bool:
        """
        Checks if a record already exists for this Obligation + Period.
        Returns True if duplicate found.
        """
        count = session.query(func.count(Vencimiento.id)).filter(
            Vencimiento.obligacion_id == obligacion_id,
            Vencimiento.periodo == periodo,
            Vencimiento.is_deleted == 0
        ).scalar()
        
        return count > 0


        return count > 0

    @staticmethod
    @safe_transaction
    def get_insights(session=None) -> list:
        """
        Generates proactive financial insights.
        Returns: List of dicts {'type': 'warning/info/good', 'text': '...'}
        """
        insights = []
        from datetime import date, timedelta
        import calendar
        
        today = date.today()
        # 1. Urgent Deadlines (Next 48h)
        # Using today + 2 days
        limit_date = today + timedelta(days=2)
        
        urgent_count = session.query(func.count(Vencimiento.id)).filter(
            Vencimiento.estado == EstadoVencimiento.PENDIENTE,
            Vencimiento.fecha_vencimiento >= today,
            Vencimiento.fecha_vencimiento <= limit_date,
            Vencimiento.is_deleted == 0
        ).scalar() or 0
        
        if urgent_count > 0:
            insights.append({
                "type": "info",
                "text": f"📅 Tienes {urgent_count} vencimientos en las próximas 48hs."
            })
            
        # 2. Inflation Alert (MoM Spending)
        # Compare current month vs prev month total (Original Amounts)
        # Current month
        curr_month_str = today.strftime("%Y-%m")
        
        # Prev month logic
        year = today.year
        month = today.month
        prev_month = month - 1
        prev_year = year
        if prev_month == 0:
            prev_month = 12
            prev_year = year - 1
        prev_month_str = f"{prev_year}-{prev_month:02d}"
        
        # Calc totals (All obligations, regardless of payment status, to see 'spending pressure')
        curr_total = session.query(func.sum(Vencimiento.monto_original)).filter(
            Vencimiento.periodo == curr_month_str,
            Vencimiento.is_deleted == 0
        ).scalar()
        curr_total = float(curr_total or 0)

        prev_total = session.query(func.sum(Vencimiento.monto_original)).filter(
            Vencimiento.periodo == prev_month_str,
            Vencimiento.is_deleted == 0
        ).scalar()
        prev_total = float(prev_total or 0)
        
        if prev_total > 0 and curr_total > prev_total:
            # Check % increase
            pct_inc = ((curr_total - prev_total) / prev_total)
            if pct_inc > 0.15: # 15% threshold
                insights.append({
                    "type": "warning",
                    "text": f"📉 Alerta Inflación: Tus gastos subieron un {int(pct_inc*100)}% vs mes anterior."
                })
        
        curr_paid_val = session.query(func.sum(Vencimiento.monto_original)).filter(
            Vencimiento.periodo == curr_month_str,
            Vencimiento.estado == EstadoVencimiento.PAGADO,
            Vencimiento.is_deleted == 0
        ).scalar()
        curr_paid_val = float(curr_paid_val or 0)

        # 3. Good News (Completion)
        # If > 90% of current month is PAID
        if curr_paid_val and curr_total > 0:
            completion = float(curr_paid_val) / curr_total
            if completion >= 0.90:
                 insights.append({
                    "type": "good",
                    "text": f"🎉 ¡Excelente! Has cubierto el {int(completion*100)}% de tus obligaciones de este mes."
                })
        
        return insights

    @staticmethod
    def predict_next_month_total(session) -> tuple[float, float, str]:
        """
        Predicts expenses for next month using Weighted Moving Average (Last 3 months).
        Returns: (PredictedAmount, ConfidenceScore, Reasoning)
        """
        from datetime import date
        today = date.today()
        
        # Get last 3 months totals
        history = []
        # Calculate prev month logic
        curr_month = today.month
        curr_year = today.year
        
        for i in range(1, 4):
            target_month = curr_month - i
            target_year = curr_year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            period_str = f"{target_year}-{target_month:02d}"
            
            t = session.query(func.sum(Vencimiento.monto_original)).filter(
                Vencimiento.periodo == period_str, 
                Vencimiento.is_deleted == 0
            ).scalar()
            history.append(float(t or 0))
            
        # history = [M-1, M-2, M-3]
        if len(history) < 3 or sum(history) == 0:
            return 0.0, 0.0, "Insuficiente data histórica."
            
        p_val = (history[0] * 0.5) + (history[1] * 0.3) + (history[2] * 0.2)
        
        trend = "constante"
        if history[0] > history[1] * 1.1: trend = "en aumento"
        elif history[0] < history[1] * 0.9: trend = "en baja"
            
        return p_val, 0.85, f"Basado en tus últimos 3 meses (Tendencia {trend})."

    @staticmethod
    def detect_price_creep(session) -> list:
        """
        Identifies services that increased price consecutively over last 3 periods.
        """
        alerts = []
        result = session.query(Vencimiento.obligacion_id).group_by(Vencimiento.obligacion_id).limit(50).all()
        obs_ids = [r[0] for r in result]
        
        for oid in obs_ids:
            recs = session.query(Vencimiento).filter(
                Vencimiento.obligacion_id == oid,
                Vencimiento.is_deleted == 0
            ).order_by(Vencimiento.fecha_vencimiento.desc()).limit(3).all()
            
            if len(recs) < 3: continue
            
            v0, v1, v2 = recs[0].monto_original, recs[1].monto_original, recs[2].monto_original
            # Threshold 1%
            if v0 > v1 * 1.01 and v1 > v2 * 1.01:
                total_inc_pct = int(((v0 - v2) / v2) * 100)
                if recs[0].obligacion and recs[0].obligacion.proveedor:
                    prov_name = recs[0].obligacion.proveedor.nombre_entidad
                    alerts.append(f"⚠️ {prov_name} aumentó un {total_inc_pct}% en 3 meses.")

        return alerts

    @staticmethod
    def get_spending_dna(session, period_id) -> dict:
        """
        Returns Categoría distribution for the period.
        """
        from models.entities import Obligacion, ProveedorServicio
        
        rows = session.query(ProveedorServicio.categoria, func.sum(Vencimiento.monto_original)).\
            join(Obligacion, Obligacion.servicio_id == ProveedorServicio.id).\
            join(Vencimiento, Vencimiento.obligacion_id == Obligacion.id).\
            filter(Vencimiento.periodo == period_id, Vencimiento.is_deleted == 0).\
            group_by(ProveedorServicio.categoria).all()
            
        total = sum([float(r[1] or 0) for r in rows])
        if total == 0: return {}
        
        dna = {}
        for cat, val in rows:
            cat_name = cat.value if hasattr(cat, 'value') else str(cat)
            pct = round((float(val) / total) * 100, 1)
            dna[cat_name] = pct
            
        return dna


