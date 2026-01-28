from datetime import date, datetime
from database import get_db, SessionLocal
from services.dashboard_service import DashboardService
from services.currency_service import CurrencyService # NEW
from utils.logger import app_logger

class DashboardController:
    def __init__(self):
        self.service = DashboardService()
        self.currency_service = CurrencyService() # NEW

    def get_executive_summary(self, currency="ARS", reference_date=None):
        """Returns DashboardDTO object. Currency: ARS or USD"""
        try:
            return self.service.get_dashboard_data(target_currency=currency, reference_date=reference_date)
        except Exception as e:
            app_logger.error(f"Error en Dashboard: {e}")
            return None


