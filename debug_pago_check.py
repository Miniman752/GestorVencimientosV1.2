import sys
import os
sys.path.append(os.path.abspath("e:/43.Gestor de vencimientos/07.Gestor de vencimientos/src_restored"))

from database import SessionLocal
from models.entities import Vencimiento, EstadoVencimiento

def check_pago():
    session = SessionLocal()
    try:
        print("\n--- CHECK PAYMENTS ---")
        rows = session.query(Vencimiento).filter(Vencimiento.estado == EstadoVencimiento.PAGADO).all()
        for v in rows:
            orig = v.monto_original
            pago = v.pagos[0].monto if v.pagos else None
            diff = (orig - pago) if pago is not None else 0
            print(f"ID: {v.id} | Per: {v.periodo} | Orig: {orig} | Paid: {pago} | Diff: {diff}")
            
    finally:
        session.close()

if __name__ == "__main__":
    check_pago()
