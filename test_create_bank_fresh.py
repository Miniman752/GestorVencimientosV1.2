
import sys
import os
import datetime
from sqlalchemy import text

# Add src to path
sys.path.append(os.getcwd())

from controllers.reconciliation_controller import ReconciliationController
from models.entities import Vencimiento, Pago, ProveedorServicio, EstadoVencimiento, CategoriaServicio
from database import SessionLocal

def test_start_fresh():
    print("--- Testing create_vencimiento (FRESH PROV) ---")
    
    session = SessionLocal()
    # 1. DELETE EXISTING PROVIDER IF ANY
    prov_name = "Banco (Conciliación)"
    try:
        prov = session.query(ProveedorServicio).filter(ProveedorServicio.nombre_entidad == prov_name).first()
        if prov:
            print(f"Deleting existing provider: {prov.nombre_entidad}")
            # Delete obligations first
            for obl in prov.obligaciones:
                # Delete vencimientos
                for v in obl.vencimientos:
                    session.delete(v)
                session.delete(obl)
            session.delete(prov)
            session.commit()
            print("Deleted.")
    except Exception as e:
        print(f"Error preparing clean state: {e}")
        session.rollback()
    finally:
        session.close()

    # 2. RUN TEST
    ctrl = ReconciliationController()
    
    today = datetime.date.today()
    period = today.strftime("%m-%Y")
    
    mock_data = {
        'fecha': today,
        'valor_db': 5000.00,
        'valor_csv': -5000.00,
        'concepto': "TEST BANK FRESH",
        'moneda': "ARS",
        'files': {}
    }
    
    print(f"Creating Vencimiento...")
    success, result = ctrl.create_vencimiento_from_bank(mock_data, period)
    
    if not success:
        print(f"FAILED: {result}")
        return

    v_id = result
    print(f"Created Vencimiento ID: {v_id}")

    session = SessionLocal()
    try:
        v = session.query(Vencimiento).get(v_id)
        
        # PROVIDER CHECK
        prov = v.obligacion.proveedor
        print(f"Proveedor Created: '{prov.nombre_entidad}'")
        print(f"Categoria Value: '{prov.categoria}'")
        
        expected_cat = CategoriaServicio.OTROS.value # "Otros"
        if prov.categoria != expected_cat:
            print(f"WARNING: Categoria mismatch! Expected '{expected_cat}', got '{prov.categoria}'")
        else:
            print("Categoria MATCH.")
            
        # STATE CHECK
        print(f"Vencimiento Estado: {v.estado}")
        if v.estado != EstadoVencimiento.PAGADO:
             print(f"WARNING: State mismatch! Expected PAGADO, got {v.estado}")
        else:
             print("State MATCH.")
             
        # Cleanup
        ctrl.delete_vencimiento(v_id)
        # Also delete provider to keep clean? No, keep it to verify persistence if needed, or delete.
        # Let's delete it.
        session.delete(v.obligacion) # Cascades?
        session.delete(prov)
        session.commit()
        print("Cleanup done.")
        
    except Exception as e:
        print(f"Error verifying: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_start_fresh()
