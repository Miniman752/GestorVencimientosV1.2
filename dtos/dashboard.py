from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class KPIData:
    deuda_exigible: float
    prevision_caja: float
    eficiencia: float
    total_ahorrado: float = 0.0
    ahorro_pct: float = 0.0

@dataclass
class ChartData:
    by_category: Dict[str, float]
    evolution: List[Dict[str, Any]]
    top_properties: Dict[str, float]

@dataclass
class TimelineItem:
    fecha: str
    detalle: str
    monto: float

@dataclass
class UXState:
    status: str
    streak: int

@dataclass
class AIInsights:
    forecast_amount: float
    forecast_confidence: float # 0.0 - 1.0
    forecast_reason: str
    price_alerts: List[str]
    spending_dna: Dict[str, float]

@dataclass
class DashboardDTO:
    kpis: KPIData
    charts: ChartData
    timeline: List[TimelineItem]
    ux_state: UXState
    ai: AIInsights = None # Optional for backward compat



