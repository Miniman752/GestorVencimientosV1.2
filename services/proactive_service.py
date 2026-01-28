
from datetime import date
from sqlalchemy import func
from database import SessionLocal
from models.entities import Vencimiento, EstadoVencimiento, PeriodoContable, EstadoPeriodo
from utils.logger import app_logger
from utils.decorators import safe_transaction

class ProactiveService:
    @staticmethod
    @safe_transaction
    def get_startup_notification(session=None):
        """
        Analyzes system state and returns a helpful suggestion/notification for the user.
        """
        try:
            today = date.today()
            msg = None
            
            # Rule 1: Period Close Suggestion (Last 5 days of month)
            import calendar
            last_day = calendar.monthrange(today.year, today.month)[1]
            if (last_day - today.day) <= 5:
                # Check if current period is open
                pid = f"{today.year}-{today.month:02d}"
                period = session.query(PeriodoContable).get(pid)
                if not period or period.estado == EstadoPeriodo.ABIERTO:
                    msg = "Estamos cerrando el mes. ¿Recuerda revisar el cierre de períodos?"

            # Rule 2: Overdue Check
            overdue_count = session.query(func.count(Vencimiento.id)).filter(
                Vencimiento.estado == EstadoVencimiento.VENCIDO,
                Vencimiento.is_deleted == 0
            ).scalar()
            
            if overdue_count and overdue_count > 0:
                # If rule 1 didn't trigger, or maybe prioritize this?
                # Let's return this if urgent
                if not msg:
                    msg = f"Atención: Hay {overdue_count} vencimientos vencidos pendientes de acción."
            
            return msg
        except Exception as e:
            app_logger.error(f"Proactive Service Error: {e}")
            return None


