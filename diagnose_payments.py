import sys
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models.entities import Vencimiento, Pago, EstadoVencimiento

# Setup DB
DATABASE_URL = "postgresql://neondb_owner:npg_vhmWRL8ESXI3@ep-green-night-acbu7krn-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

def log(msg):
    print(msg)
    sys.stdout.flush()

log("--- DIAGNOSTICO DE DATOS (V2) ---")

# 1. Inspect Period from user Context (Likely 2025-12 based on screenshots showing dates in Dec 2025)
# User mentions 19 records.
# Let's count by period to find which one has 19.
periods = session.query(Vencimiento.periodo, func.count(Vencimiento.id)).filter(Vencimiento.is_deleted == 0).group_by(Vencimiento.periodo).all()
log(f"Recuentos por Periodo: {periods}")

target_period = "2025-12" # Guessing from screenshot showing Dec dates
log(f"Analizando Periodo: {target_period}")

# 2. Vencimientos in Period
vencs = session.query(Vencimiento).filter(Vencimiento.is_deleted == 0, Vencimiento.periodo == target_period).all()
log(f"Total Vencimientos en {target_period}: {len(vencs)}")

paid = [v for v in vencs if v.estado == EstadoVencimiento.PAGADO]
pending = [v for v in vencs if v.estado == EstadoVencimiento.PENDIENTE]

log(f"  - Pagados: {len(paid)}")
log(f"  - Pendientes: {len(pending)}")

# 3. Pagos linked to these Vencimientos
paid_ids = [v.id for v in paid]
pagos = session.query(Pago).filter(Pago.vencimiento_id.in_(paid_ids)).all()
log(f"Pagos encontrados para los vencimientos pagados: {len(pagos)}")

# 4. Check discrepancies
# Are there Paid Vencimientos with NO payments?
vencs_with_payments = set([p.vencimiento_id for p in pagos])
vencs_without_payments = [v.id for v in paid if v.id not in vencs_with_payments]

if vencs_without_payments:
    log(f"ALERTA: Vencimientos marcados PAGADO sin registro en tabla Pagos: {len(vencs_without_payments)}")
    for vid in vencs_without_payments:
        log(f"  -> ID {vid}")
else:
    log("Todos los vencimientos pagados tienen al menos 1 pago.")

# Are there Paid Vencimientos with MULTIPLE payments?
from collections import Counter
counts = Counter([p.vencimiento_id for p in pagos])
multi = {k:v for k,v in counts.items() if v > 1}
if multi:
    log(f"ALERTA: Vencimientos con múltiples pagos: {multi}")
else:
    log("Ningún vencimiento tiene múltiples pagos.")

# Check Date Range of Payments vs View Range
# Treasury View defaults to "Current Month" (Jan 2026?).
# User might be looking at Dec 2025 Vencimientos but Treasury View is showing Jan 2026 Payments?
# Or if filter is cleared, maybe showing all?
# Let's check dates of payments.
if pagos:
    dates = [p.fecha_pago for p in pagos]
    log(f"Rango de Fechas de Pagos: {min(dates)} a {max(dates)}")

# Check Pending Vencimientos with Payments?
pending_ids = [v.id for v in pending]
pagos_pending = session.query(Pago).filter(Pago.vencimiento_id.in_(pending_ids)).all()
if pagos_pending:
    log(f"ALERTA: Pagos asociados a Vencimientos PENDIENTES: {len(pagos_pending)}")
else:
    log("Correcto: No hay pagos en vencimientos pendientes.")
