
import sys
import os
import io
import datetime

# Add src to path
sys.path.append(os.getcwd())

from controllers.reconciliation_controller import ReconciliationController
from models.entities import Vencimiento, Pago, ProveedorServicio, EstadoVencimiento
from database import SessionLocal

def test_create_from_bank():
    print("--- Testing create_vencimiento_from_bank ---")
    ctrl = ReconciliationController()
    
    # Dummy Data
    today = datetime.date.today()
    mock_data = {
        'fecha': today,
        'valor_db': 1234.56,
        'valor_csv': -1234.56, # Assuming bank outflow
        'concepto': "TEST BANK TRANSACTION",
        'moneda': "ARS",
        'files': {}
    }
    period = today.strftime("%m-%Y")
    
    # 1. Execute
    print(f"Creating Vencimiento for {period} with amount {mock_data['valor_db']}...")
    success, result = ctrl.create_vencimiento_from_bank(mock_data, period)
    
    if not success:
        print(f"FAILED: {result}")
        return
        
    v_id = result
    print(f"SUCCESS. Vencimiento ID: {v_id}")
    
    # 2. Verify DB
    session = SessionLocal()
    try:
        v = session.query(Vencimiento).get(v_id)
        assert v is not None
        print(f"Vencimiento Found: {v.id}")
        print(f"  Estado: {v.estado}")
        print(f"  Monto: {v.monto_original}")
        print(f"  Obligacion ID: {v.obligacion_id}")
        
        # Verify Provider
        prov = v.obligacion.proveedor
        print(f"  Proveedor: {prov.nombre_entidad} (Cat: {prov.categoria})")
        
        # Verify Pago
        pago = session.query(Pago).filter(Pago.vencimiento_id == v_id).first()
        assert pago is not None
        print(f"Pago Found: {pago.id}, Monto: {pago.monto}")
        
        # Check Enums
        # state should be PAGADO
        # category should be "Otros"
        
        real_state = v.estado
        print(f"Enum Check - Vencimiento.estado type: {type(real_state)}, Value: {real_state}")
        
        real_cat = prov.categoria
        print(f"Enum Check - Proveedor.categoria type: {type(real_cat)}, Value: {real_cat}")
        
        # 3. Cleanup
        print("Cleaning up...")
        success_del, msg = ctrl.delete_vencimiento(v_id)
        if success_del:
            print("Cleanup Successful.")
        else:
            print(f"Cleanup Failed: {msg}")
            
    except Exception as e:
        print(f"Verification Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_create_from_bank()
