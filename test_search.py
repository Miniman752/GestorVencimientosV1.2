
import sys
import os
sys.path.append(os.path.join(os.getcwd()))
from database import SessionLocal
from models.entities import Vencimiento, EstadoVencimiento, Obligacion, ProveedorServicio
from sqlalchemy.orm import joinedload

def test():
    db = SessionLocal()
    try:
        print("1. Basic Query...")
        cnt = db.query(Vencimiento).count()
        print(f"Total Vencimientos: {cnt}")
        
        print("2. Filter Pendiente...")
        q = db.query(Vencimiento).filter(Vencimiento.estado == EstadoVencimiento.PENDIENTE)
        print(f"Pending: {q.count()}")
        
        print("3. Check is_deleted...")
        try:
            q = q.filter(Vencimiento.is_deleted == 0)
            print(f"Pending & Not Deleted: {q.count()}")
        except Exception as e:
            print(f"is_deleted Failed: {e}")
            
        print("4. Join Obligacion...")
        try:
            q = db.query(Vencimiento).join(Vencimiento.obligacion)
            print(f"Joined Obligacion: {q.count()}")
        except Exception as e:
            print(f"Join Obligacion Failed: {e}")

        print("5. Join Proveedor...")
        try:
             q = db.query(Vencimiento).join(Vencimiento.obligacion).join(Obligacion.proveedor)
             print(f"Joined Proveedor: {q.count()}")
        except Exception as e:
             print(f"Join Proveedor Failed: {e}")

    except Exception as e:
        print(f"CRITICAL: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test()
