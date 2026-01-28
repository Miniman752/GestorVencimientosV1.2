from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import date

@dataclass
class SimulationParams:
    start_date: date
    months_to_project: int = 12
    monthly_inflation_pct: float = 0.0
    future_usd_value: float = 0.0 # If 0, use current

@dataclass
class ProjectionItem:
    period: str # YYYY-MM
    category: str
    description: str # Provider or details
    amount_projected: float
    is_fixed: bool # To separate Fixed vs Variable in charts

@dataclass
class BudgetDTO:
    items: List[ProjectionItem]
    total_by_month: Dict[str, float]
    total_by_category: Dict[str, float]
    alerts: List[str] # e.g. "Deficit in Oct"


