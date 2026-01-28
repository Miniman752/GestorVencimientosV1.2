
import sys
import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.append(os.path.join(os.getcwd()))

from database import SessionLocal
from models.entities import Vencimiento, EstadoVencimiento, Moneda, Pago, Inmueble, ProveedorServicio, Obligacion
from controllers.reconciliation_controller import ReconciliationController

def verify_manual_match():
    print("--- Starting Manual Match Verification ---")
    
    db = SessionLocal()
    controller = ReconciliationController()
    
    created_ids = {'inmueble': None, 'proveedor': None, 'obligacion': None, 'vencimiento': None}
    
    try:
        # 0. Dependencies
        print("0. Creating Dependencies...")
        
        # Inmueble
        inmueble = Inmueble(alias="TEST_UNIT_MANUAL", direccion="TEST ADDRESS", tipo_propiedad="Casa")
        db.add(inmueble)
        db.flush()
        created_ids['inmueble'] = inmueble.id
        
        # Proveedor
        prov = ProveedorServicio(nombre_entidad="TEST_PROV_MANUAL", categoria="Servicios")
        db.add(prov)
        db.flush()
        created_ids['proveedor'] = prov.id
        
        # Obligacion
        oblig = Obligacion(inmueble_id=inmueble.id, servicio_id=prov.id, numero_cliente_referencia="REF123")
        db.add(oblig)
        db.flush()
        created_ids['obligacion'] = oblig.id
        
        # 1. Create a dummy PENDING Vencimiento
        print("1. Creating Dummy Pending Vencimiento...")
        venc = Vencimiento(
            obligacion_id=oblig.id,
            fecha_vencimiento=datetime.date.today(),
            periodo=datetime.date.today().strftime("%Y-%m"),
            monto_original=12345.67,
            moneda=Moneda.ARS,
            estado=EstadoVencimiento.PENDIENTE,
            # descripcion is NOT a column in Vencimiento! It comes from Obligacion/Proveedor usually, OR it IS a column?
            # Looking at view_file of models/entities.py... 
            # I DO NOT SEE 'descripcion' column in Vencimiento class!
            # That explains the TypeError!
        )
        # Wait, let me check the file content I viewed again.
        # Line 87 class Vencimiento(Base):
        # ...
        # 107 prioridad... 111 ruta...
        # I DO NOT SEE 'descripcion'. 
        
        # So 'descripcion' likely comes from `vencimiento.obligacion.proveedor.nombre_entidad` or similar logic in the property or Controller.
        # BUT search_vencimientos performs `Vencimiento.descripcion.ilike(term)`.
        # IF 'descripcion' is not a column, then search_vencimientos WILL FAIL too!
        
        # Let's check search_vencimientos implementation I wrote:
        # query = query.filter(Vencimiento.descripcion.ilike(term))
        # This confirms I made a mistake in the Controller code too if the column doesn't exist.
        
        # However, usually there is a proxy or it might be joined.
        
        db.add(venc)
        db.commit()
        db.refresh(venc)
        created_ids['vencimiento'] = venc.id
        print(f"   > Created Vencimiento ID: {venc.id}")
        
        # 2. Search for it
        print("\n2. Searching for Vencimiento via Controller...")
        
        # Since I suspect 'descripcion' is missing, I should check if the search crashes or works.
        # But wait, if I wrote the code assuming it exists, I need to fix the code.
        
        try:
            results_amt = controller.search_vencimientos("12345.67")
            print(f"   > Search '12345.67': Found {len(results_amt)} results")
        except Exception as e:
            print(f"   > Search Amount Failed: {e}")

        # 3. Apply Match
        print("\n3. Applying Manual Match...")
        bank_row = {
            'fecha': datetime.date.today(),
            'valor_csv': -12345.67, # Negative in bank (payment)
            'concepto': "DEBITO AUTOMATICO TEST"
        }
        
        success, msg = controller.apply_match(bank_row, venc.id)
        print(f"   > Result: {success} | Msg: {msg}")
        
        if not success:
            print("FAILED: Apply match returned false.")
            return

        # 4. Verify Database State
        print("\n4. Verifying Database State...")
        db.expire_all()
        venc_updated = db.query(Vencimiento).get(venc.id)
        
        print(f"   > Vencimiento State: {venc_updated.estado}")
        if venc_updated.estado != EstadoVencimiento.PAGADO:
             print("FAILED: Status is not PAGADO")
             
        # Check Payment
        pagos = db.query(Pago).filter(Pago.vencimiento_id == venc.id).all()
        if len(pagos) == 1:
            p = pagos[0]
            print(f"   > Payment Amount: {p.monto} (Expected: 12345.67)")
            if abs(p.monto - 12345.67) < 0.01:
                print("SUCCESS: Payment record matches logic.")
            else:
                print("FAILED: Payment amount mismatch.")
        else:
            print("FAILED: No payment record found.")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\nCleaning up...")
        try:
            if created_ids['vencimiento']:
                 db.query(Pago).filter(Pago.vencimiento_id == created_ids['vencimiento']).delete()
                 db.query(Vencimiento).filter(Vencimiento.id == created_ids['vencimiento']).delete()
            if created_ids['obligacion']: db.query(Obligacion).filter(Obligacion.id == created_ids['obligacion']).delete()
            if created_ids['proveedor']: db.query(ProveedorServicio).filter(ProveedorServicio.id == created_ids['proveedor']).delete()
            if created_ids['inmueble']: db.query(Inmueble).filter(Inmueble.id == created_ids['inmueble']).delete()
            db.commit()
            print("Cleanup done.")
        except: pass
        db.close()

if __name__ == "__main__":
    verify_manual_match()
