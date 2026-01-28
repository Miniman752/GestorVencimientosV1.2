from database import SessionLocal
from models.entities import Vencimiento, EstadoVencimiento, Inmueble, Obligacion, Pago
from sqlalchemy import func

session = SessionLocal()
def test_q(name, q):
    try:
        res = q.scalar() if hasattr(q, 'scalar') else q.all()
        print(f"{name}: SUCCESS")
    except Exception as e:
        print(f"{name}: FAILED - {e}")

try:
    print("Testing individual queries...")
    
    test_q("total_deuda", session.query(func.sum(Vencimiento.monto_original)).filter(Vencimiento.is_deleted == 0))
    test_q("total_pagado", session.query(func.sum(Pago.monto)))
    test_q("pendientes", session.query(func.count(Vencimiento.id)).filter(Vencimiento.is_deleted == 0))
    
    test_q("prop_stats", session.query(Inmueble.id, func.count(Vencimiento.id)).join(Obligacion, Vencimiento.obligacion_id == Obligacion.id).join(Inmueble, Obligacion.inmueble_id == Inmueble.id))

    test_q("monthly", session.query(Vencimiento.periodo, func.sum(Vencimiento.monto_original)).group_by(Vencimiento.periodo))

finally:
    session.close()
