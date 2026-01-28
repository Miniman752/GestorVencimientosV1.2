import sys
import os
sys.path.append(os.path.abspath("e:/43.Gestor de vencimientos/07.Gestor de vencimientos/src_restored"))

from database import SessionLocal
from models.entities import Vencimiento, EstadoVencimiento

def debug_clean():
    session = SessionLocal()
    try:
        print("\n--- CLEAN DEBUG ---")
        rows = session.query(Vencimiento).filter(Vencimiento.estado == EstadoVencimiento.PAGADO).all()
        for v in rows:
            pago = v.pagos[0].monto if v.pagos else 0.0
            deleted = v.is_deleted
            print(f"ID:{v.id} P:{v.periodo} Del:{deleted} Orig:{v.monto_original} Paid:{pago}")
    finally:
        session.close()

if __name__ == "__main__":
    debug_clean()
