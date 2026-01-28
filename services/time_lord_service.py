import pandas as pd
from decimal import Decimal
from sqlalchemy import func
from datetime import date, timedelta
from typing import List
from models.entities import Vencimiento, IndiceEconomico, EstadoVencimiento
from dtos.analysis import AnalysisRequestDTO, AnalysisResponseDTO, HeatmapDTO, ComparativeDTO, SeasonalityAlertDTO
from utils.decorators import safe_transaction
from utils.logger import app_logger

class TimeLordService:
    @safe_transaction
    def get_analysis(self, request: AnalysisRequestDTO, session=None) -> AnalysisResponseDTO:
        # 1. Fetch Raw Data
        query = session.query(Vencimiento.fecha_vencimiento, Vencimiento.monto_original).filter(
            Vencimiento.fecha_vencimiento >= request.start_date,
            Vencimiento.fecha_vencimiento <= request.end_date,
            Vencimiento.estado != EstadoVencimiento.REVISION, # Exclude drafts if any
            Vencimiento.is_deleted == 0 # Exclude soft-deleted items
        )
        data = query.all() # List of tuples

        if not data:
            return AnalysisResponseDTO([], [], [], [], 0.0)

        # 2. Pandas Transformation
        df = pd.DataFrame(data, columns=['date', 'amount'])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        # Ensure 'amount' is Decimal for consistent arithmetic
        df['amount'] = df['amount'].apply(lambda x: Decimal(str(x)) if x is not None else Decimal("0"))

        # 3. Inflation Adjustment
        if request.adjust_inflation:
            # Fetch all indices sorted by date ASC for cumulative calculation
            indices = session.query(IndiceEconomico).order_by(IndiceEconomico.periodo.asc()).all()
            
            if indices:
                cpi_map = self._build_cpi_curve(indices)
                
                # Determine Target Index (Latest available)
                # Use the last key in the map (most recent date)
                if cpi_map:
                    latest_period = max(cpi_map.keys())
                    target_index = cpi_map[latest_period]
                    
                    # Define a function to apply to each row
                    def adjust_row(row):
                        # Row index is datetime
                        period_key = row.name.strftime("%Y-%m")
                        # Get source index for this period, or fallback to closest previous if missing?
                        # For now, if missing, assume 1.0 (no adjustment possible or data missing)
                        # Better: find closest key? 
                        # Simple approach: exact match or fallback to 1.0 (no change) in logic below
                        
                        source_index = cpi_map.get(period_key)
                        
                        if source_index and source_index > 0:
                            # Formula: Amount * (Target / Source)
                            factor = target_index / source_index
                            return row['amount'] * Decimal(str(factor))
                        return row['amount']

                    # Apply adjustment
                    # Note: df.apply with axis=1 passes row. But here 'amount' is a Series if we select it?
                    # df is DataFrame with index 'date' and col 'amount'.
                    # Iterating might be safer for types or simple apply on the column if we can map index.
                    
                    # Vectorized approach likely faster but complex with dict lookup.
                    # Row-wise apply:
                    df['amount'] = df.apply(adjust_row, axis=1)


        # 4. Aggregation (Granularity)
        rule_map = {"D": "D", "W": "W", "M": "ME", "Q": "QE", "Y": "YE"} # pandas 2.0+ uses 'ME' for Month End
        # Fallback for older pandas if needed: 'M', 'Q', 'A'
        try:
            resampled = df.resample(rule_map.get(request.granularity, "ME")).sum()
        except ValueError:
             # Fallback for older pandas versions
             legacy_map = {"D": "D", "W": "W", "M": "M", "Q": "Q", "Y": "A"}
             resampled = df.resample(legacy_map.get(request.granularity, "M")).sum()

        time_series = []
        for dt, row in resampled.iterrows():
            if row['amount'] > 0: # Filter empty periods? Maybe keep for continuity
                time_series.append({
                    "date": dt.strftime("%Y-%m-%d"), 
                    "value": row['amount']
                })

        # 5. Heatmap (Daily concentration)
        # Re-query or reuse df, but full daily range
        daily_df = df.resample('D').sum()
        max_val = daily_df['amount'].max() if not daily_df.empty else 1
        heatmap = []
        for dt, row in daily_df.iterrows():
            if row['amount'] > 0:
                heatmap.append(HeatmapDTO(
                    date_str=dt.strftime("%Y-%m-%d"),
                    value=row['amount'],
                    intensity=row['amount'] / max_val if max_val > 0 else 0
                ))

        # 6. Seasonality (Naive implementation)
        # Check historical average of this month vs annual average
        # Requires wider context than request range, usually. 
        # For this iteration, we look for spikes > 1.5 * mean in the loaded range
        mean_val = resampled['amount'].mean()
        # Fix: mean_val from pandas/statistics might be float, amount is Decimal
        mean_val_dec = Decimal(str(mean_val)) if mean_val is not None else Decimal(0)

        seasonality = []
        for dt, row in resampled.iterrows():
            # row['amount'] is Decimal
            if row['amount'] > mean_val_dec * Decimal("1.5"):
                pct_increase = Decimal(0)
                if mean_val_dec and mean_val_dec > 0:
                     pct_increase = ((row['amount'] - mean_val_dec) / mean_val_dec) * 100
                
                seasonality.append(SeasonalityAlertDTO(
                    month=dt.strftime("%B"),
                    avg_increase_pct=pct_increase,
                    message=f"High expense detected in {dt.strftime('%B')}"
                ))

        # 7. Comparative (MoM of last 2 periods in range)
        comparative = []
        if len(resampled) >= 2:
            last = resampled.iloc[-1]['amount']
            prev = resampled.iloc[-2]['amount']
            diff = last - prev
            pct = (diff / prev * 100) if prev != 0 else 0
            comparative.append(ComparativeDTO(
                label="Growth (Last 2 Pers)",
                value=pct,
                is_positive_bad=True
            ))

        return AnalysisResponseDTO(
            time_series=time_series,
            heatmap=heatmap,
            comparative=comparative,
            seasonality=seasonality,
            total_period=df['amount'].sum()
        )

    def _build_cpi_curve(self, indices: List[IndiceEconomico]) -> dict:
        """
        Reconstructs a Cumulative Price Index (CPI) curve from monthly variation percentages.
        Base 1.0 at start.
        Returns map: { "YYYY-MM": Decimal(cumulative_index) }
        """
        cpi_map = {}
        current_index = Decimal("1.0")
        
        for idx in indices:
            # idx.valor is Monthly Percentage (e.g. 4.5 for 4.5%)
            # Formula: NewIndex = OldIndex * (1 + Pct/100)
            
            val = Decimal(str(idx.valor)) if idx.valor is not None else Decimal("0")
            monthly_factor = (val / Decimal("100")) + Decimal("1")
            current_index = current_index * monthly_factor
            
            key = idx.periodo.strftime("%Y-%m")
            cpi_map[key] = current_index
            
        return cpi_map

    # --- CRUD for Inflation Indices (Module 21) ---

    @safe_transaction
    def get_all_indices(self, session=None) -> List[IndiceEconomico]:
        """Returns all indices sorted by date descending."""
        return session.query(IndiceEconomico).order_by(IndiceEconomico.periodo.desc()).all()

    @safe_transaction
    def add_index(self, period: date, value: Decimal, source: str = "Manual", session=None) -> IndiceEconomico:
        """Adds a new inflation index."""
        # Check for duplicates
        existing = session.query(IndiceEconomico).filter_by(periodo=period).first()
        if existing:
            raise ValueError(f"Ya existe un índice registrado para el período {period.strftime('%m/%Y')}.")
        
        new_idx = IndiceEconomico(
            periodo=period,
            valor=value
        )
        session.add(new_idx)
        return new_idx

    @safe_transaction
    def update_index(self, idx_id: int, value: Decimal, session=None) -> IndiceEconomico:
        """Updates an existing index value."""
        idx = session.query(IndiceEconomico).get(idx_id)
        if not idx:
            raise ValueError(f"No se encontró el índice con ID {idx_id}.")
        idx.valor = value
        return idx

    @safe_transaction
    def delete_index(self, idx_id: int, session=None):
        """Deletes an index."""
        idx = session.query(IndiceEconomico).get(idx_id)
        if not idx:
            raise ValueError(f"No se encontró el índice con ID {idx_id}.")
        session.delete(idx)


