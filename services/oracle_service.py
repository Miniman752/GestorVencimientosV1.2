from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from models.entities import Obligacion, Vencimiento, TipoAjuste, Moneda, EstadoInmueble
from dtos.oracle import BudgetDTO, ProjectionItem, SimulationParams
from utils.decorators import safe_transaction
from services.forex_service import ForexService

class OracleService:
    def __init__(self):
        self.forex = ForexService()

    @safe_transaction
    def project_budget(self, params: SimulationParams, session: Session = None) -> BudgetDTO:
        # 1. Get Active Obligations (Active Property AND Active Provider)
        # We must join Provider to check 'activo' flag
        obligations = session.query(Obligacion).join(Obligacion.inmueble).join(Obligacion.proveedor).filter(
            Obligacion.inmueble.has(), # Just check existence (no estado definition)
            Obligacion.proveedor.has() # Just check existence (no activo column)
        ).all()

        projection_items = []
        monthly_totals = {}
        category_totals = {}
        alerts = []

        current_month = params.start_date.replace(day=1)
        
        # DEBUG: User Validation
        print(f"--- 🔮 ORACLE SIMULATION STARTED ---")
        print(f" > Inflation (Monthly): {params.monthly_inflation_pct}%")
        print(f" > Future USD Value: ${params.future_usd_value} (0 = Use Database Rate)")
        # ------------------------
        
        # --- OPTIMIZATION: Pre-fetch last known payments ---
        # Instead of querying inside the loop (Months * Obligations queries), 
        # we query once per obligation (Obligations queries) or even better, bulk load.
        # For simplicity and safety, we do one query per obligation here, outside the loop.
        
        obl_snapshot = []
        
        for obl in obligations:
            last_venc = session.query(Vencimiento).filter(
                Vencimiento.obligacion_id == obl.id
            ).order_by(Vencimiento.fecha_vencimiento.desc()).first()
            
            base_amount = last_venc.monto_original if last_venc else 0.0
            curr = last_venc.moneda if last_venc else Moneda.ARS
            
            # Frequency Setup
            freq_map = {
                "Mensual": 1,
                "Bimestral": 2,
                "Trimestral": 3,
                "Cuatrimestral": 4,
                "Semestral": 6,
                "Anual": 12
            }
            # Handle missing column gracefully
            prov_freq = getattr(obl.proveedor, 'frecuencia_defecto', "Mensual")
            freq_months = freq_map.get(prov_freq, 1)
            
            # Store snapshot
            obl_snapshot.append({
                "obl": obl,
                "base_amount": base_amount,
                "currency": curr,
                "freq_months": freq_months,
                "last_venc_date": last_venc.fecha_vencimiento if last_venc else None
            })
            
        # Current USD Rate for fallback
        current_usd_rate = self.forex.get_rate(date.today(), session)

        for i in range(params.months_to_project):
            period_date = current_month + relativedelta(months=i)
            period_str = period_date.strftime("%Y-%m")
            
            # Calculate compounded inflation factor for this month relative to start
            # (1 + rate)^i
            inf_factor = (1 + params.monthly_inflation_pct / 100) ** i

            for item in obl_snapshot:
                obl = item["obl"]
                base_amount = item["base_amount"]
                curr = item["currency"]
                freq_months = item["freq_months"]
                last_venc_date = item["last_venc_date"]
                
                # Determine adjustment rule
                rule = obl.reglas_ajuste 
                algo = rule.tipo_ajuste if rule else TipoAjuste.FIJO
                
                # --- FREQUENCY CHECK ---
                if freq_months > 1 and last_venc_date:
                    proj_dt = period_date.replace(day=1)
                    last_dt = last_venc_date.replace(day=1)
                    
                    # diff in months
                    diff = (proj_dt.year - last_dt.year) * 12 + (proj_dt.month - last_dt.month)
                    
                    if diff <= 0 or (diff % freq_months != 0):
                        continue # SKIP this month
                
                projected_amount = base_amount

                # --- ALGORITHMS ---
                if algo == TipoAjuste.FIJO:
                    pass # Stays same (in original currency)
                
                elif algo == TipoAjuste.ESTACIONAL_IPC:
                    # Apply inflation
                    projected_amount = float(base_amount) * float(inf_factor)
                
                elif algo == TipoAjuste.PROMEDIO_MOVIL_3M:
                    # Simplify as inflation driven for projection
                    projected_amount = float(base_amount) * float(inf_factor)

                elif algo == TipoAjuste.INDICE_CONTRATO:
                     # For projection purposes, Manual/IPC follow the inflation curve
                     projected_amount = float(base_amount) * float(inf_factor)
                
                else:
                    # Fallback for others (DOLAR, etc): Default to inflation if not explicitly fixed
                    projected_amount = float(base_amount) * float(inf_factor)

                # --- CURRENCY SIMULATION ---
                final_amount_ars = 0.0
                if curr == Moneda.USD:
                    if params.future_usd_value > 0:
                        final_amount_ars = projected_amount * params.future_usd_value
                    else:
                        final_amount_ars = projected_amount * current_usd_rate
                else:
                    final_amount_ars = projected_amount

                # Add to list
                is_fixed_cost = (algo == TipoAjuste.FIJO)
                cat_name = obl.proveedor.categoria if obl.proveedor else "General"
                prov_name = obl.proveedor.nombre_entidad if obl.proveedor else "Obligación"
                
                # Ensure float for consistency in DTO and View calculations
                final_amount_ars = float(final_amount_ars)

                p_item = ProjectionItem(
                    period=period_str,
                    category=cat_name,
                    description=prov_name,
                    amount_projected=final_amount_ars,
                    is_fixed=is_fixed_cost
                )
                projection_items.append(p_item)

                # Accumulators
                monthly_totals[period_str] = monthly_totals.get(period_str, 0) + float(final_amount_ars)
                category_totals[cat_name] = category_totals.get(cat_name, 0) + float(final_amount_ars)

        # Sort items
        return BudgetDTO(
            items=projection_items,
            total_by_month=monthly_totals,
            total_by_category=category_totals,
            alerts=alerts
        )


