import sys
import os
sys.path.append(os.path.abspath("e:/43.Gestor de vencimientos/07.Gestor de vencimientos/src_restored"))

from database import SessionLocal
from models.entities import Vencimiento, EstadoVencimiento

def debug_simple():
    session = SessionLocal()
    try:
        print("\n--- CHECKING PAID RECORDS ---")
        rows = session.query(Vencimiento).filter(Vencimiento.estado == EstadoVencimiento.PAGADO).all()
        for v in rows:
            pago_monto = v.pagos[0].monto if v.pagos else "None"
            print(f"ID: {v.id} | Per: '{v.periodo}' | Date: {v.fecha_vencimiento} | Orig: {v.monto_original} | Paid: {pago_monto}")
            
    finally:
        session.close()

if __name__ == "__main__":
    debug_simple()
