from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.entities import Vencimiento, Pago, EstadoVencimiento

DATABASE_URL = "postgresql://neondb_owner:npg_vhmWRL8ESXI3@ep-green-night-acbu7krn-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

print("START_DIAGNOSTIC")
vencs = session.query(Vencimiento).filter(Vencimiento.is_deleted == 0, Vencimiento.periodo == "2025-12").all()
paid = [v for v in vencs if v.estado == EstadoVencimiento.PAGADO]
pending = [v for v in vencs if v.estado == EstadoVencimiento.PENDIENTE]

print(f"TOTAL: {len(vencs)}")
print(f"PAID: {len(paid)}")
print(f"PENDING: {len(pending)}")

# Pagos linked to Paid Bills
paid_ids = [v.id for v in paid]
if paid_ids:
    pagos = session.query(Pago).filter(Pago.vencimiento_id.in_(paid_ids)).all()
    print(f"PAGOS_FOR_PAID: {len(pagos)}")
    
    # Check if any Paid Bill has NO payment
    linked_vids = set(p.vencimiento_id for p in pagos)
    unpaid_bills = [vid for vid in paid_ids if vid not in linked_vids]
    print(f"PAID_BILLS_WITHOUT_PAYMENT: {len(unpaid_bills)}")
else:
    print("PAGOS_FOR_PAID: 0")

print("END_DIAGNOSTIC")
