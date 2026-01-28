from datetime import date
from database import SessionLocal
from models.entities import IndiceEconomico
from sqlalchemy import desc
from utils.decorators import safe_transaction

class EconomicService:
    # [REMOVED] Legacy add_indice in favor of add_index (Module 21)

    @staticmethod
    @safe_transaction
    def get_recent_indices(limit=12, session=None):
        return session.query(IndiceEconomico).order_by(desc(IndiceEconomico.periodo)).limit(limit).all()

    @staticmethod
    @safe_transaction
    def calculate_inflation_factor(start_date: date, end_date: date, session=None):
        """
        Calculates compounded inflation multiplier. 
        Multiplier = (1 + month1/100) * (1 + month2/100) ...
        """
        indices = session.query(IndiceEconomico).filter(
            IndiceEconomico.periodo >= start_date,
            IndiceEconomico.periodo < end_date 
        ).all()
        
        factor = 1.0
        for idx in indices:
            factor *= (1 + idx.valor / 100.0)
            
        return factor


