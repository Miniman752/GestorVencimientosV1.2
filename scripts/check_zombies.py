import sys
import os

# Setup Paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db_engine, SessionLocal
from models.entities import Vencimiento, Pago, Obligacion
from config import load_last_db_path

def check_zombies():
    print("--- DIAGNOSTICO DE REGISTROS ZOMBIE ---")
    
    # Load DB
    db_path = load_last_db_path()
    if not db_path:
        print("No hay base de datos configurada.")
        return

    if db_path.startswith("postgresql"):
        url = db_path
    else:
        url = f"sqlite:///{db_path}"
    
    try:
        init_db_engine(url)
    except Exception as e:
        print(f"Error conectando a DB: {e}")
        return

    session = SessionLocal()
    
    try:
        # 1. Pagos Huérfanos (Vencimiento Deleted)
        zombie_payments = session.query(Pago).join(Vencimiento).filter(
            Vencimiento.is_deleted == 1
        ).all()
        
        print(f"\n[1] Pagos referenciando Vencimientos Eliminados (ZOMBIES): {len(zombie_payments)}")
        if zombie_payments:
            print("    -> Estos pagos aparecen en los reportes aunque borraste el vencimiento!")
            for p in zombie_payments[:5]:
                print(f"       - Pago ID {p.id} ($ {p.monto}) -> Venc ID {p.vencimiento_id} (DELETED)")
                
        # 2. Vencimientos Huérfanos (Obligacion Missing - Hard delete logic, unlikely with FK but check)
        # SQLAlchemy usually handles FKs, but if logic allows...
        # Check logic integrity... is_deleted count
        deleted_vencs = session.query(Vencimiento).filter(Vencimiento.is_deleted == 1).count()
        print(f"\n[2] Vencimientos en Papelera (Soft Deleted): {deleted_vencs}")
        
        # 3. Check Treasury Query Simulation (Without Filter)
        # Simulate what the View sees
        view_zombies = session.query(Pago).join(Vencimiento).filter(
            Vencimiento.is_deleted == 1
        ).count()
        
        if view_zombies > 0:
            print(f"\n>>> ALERTA: Tienes {view_zombies} pagos 'Zombie' visibles en Caja/Tesorería.")
        else:
            print("\n>>> Todo limpio. No se detectaron inconsistencias críticas.")
            
    except Exception as e:
        print(f"Error durante diagnóstico: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_zombies()
