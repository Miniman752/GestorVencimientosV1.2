from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import date

@dataclass
class AnalysisRequestDTO:
    start_date: date
    end_date: date
    granularity: str # "D", "W", "M", "Y"
    adjust_inflation: bool = False

@dataclass
class HeatmapDTO:
    date_str: str
    value: float
    intensity: float # 0.0 to 1.0

@dataclass
class ComparativeDTO:
    label: str # e.g. "YoY Growth"
    value: float # Percentage or absolute diff
    is_positive_bad: bool = True # True for expenses (increase is bad)

@dataclass
class SeasonalityAlertDTO:
    month: str
    avg_increase_pct: float
    message: str

@dataclass
class AnalysisResponseDTO:
    time_series: List[Dict[str, Any]] # [{"date": "...", "value": ...}]
    heatmap: List[HeatmapDTO]
    comparative: List[ComparativeDTO]
    seasonality: List[SeasonalityAlertDTO]
    total_period: float


