from database import SessionLocal
from models.entities import Vencimiento, EstadoVencimiento, Inmueble, Obligacion, Pago
from sqlalchemy import func, text

session = SessionLocal()
try:
    print("Testing Raw SQL query...")
    prop_query = text("""
        SELECT i.alias, COUNT(v.id) as count
        FROM vencimientos v
        JOIN obligaciones o ON v.obligacion_id = o.id
        JOIN inmuebles i ON o.inmueble_id = i.id
        WHERE v.is_deleted = 0 AND v.estado != 'PAGADO'
        GROUP BY i.alias
    """)
    res = session.execute(prop_query).fetchall()
    print(f"RESULT: {res}")
except Exception as e:
    print(f"FAILED: {e}")
finally:
    session.close()
