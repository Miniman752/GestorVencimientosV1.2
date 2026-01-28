import sys
import os
sys.path.append(os.path.abspath("e:/43.Gestor de vencimientos/07.Gestor de vencimientos/src_restored"))

from database import SessionLocal
from models.entities import Vencimiento

def debug_search():
    session = SessionLocal()
    try:
        print("\n--- SEARCH BY AMOUNT ---")
        # 704542.99
        # Exact match might fail due to float, look for range
        target = 704542.99
        min_v = target - 1.0
        max_v = target + 1.0
        
        rows = session.query(Vencimiento).filter(
            Vencimiento.monto_original >= min_v,
            Vencimiento.monto_original <= max_v
        ).all()
        
        for v in rows:
            print(f"ID:{v.id} Period:{v.periodo} Status:{v.estado} Orig:{v.monto_original} Deleted:{v.is_deleted}")
            if v.pagos:
                 print(f"   -> Paid: {[p.monto for p in v.pagos]}")
            else:
                 print("   -> Paid: None")
    finally:
        session.close()

if __name__ == "__main__":
    debug_search()
