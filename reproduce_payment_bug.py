import sys
import os
import traceback

# Add current directory to sys.path directly
sys.path.append(os.getcwd())

from datetime import date
from database import SessionLocal
from models.entities import Vencimiento, EstadoVencimiento, Obligacion, Proveedor, Inmueble, TipoInmueble, CategoriaProveedor
from controllers.vencimientos_controller import VencimientosController

def reproduce_issue():
    session = SessionLocal()
    try:
        print("1. Setup Data...")
        inm = session.query(Inmueble).filter_by(alias="TEST_DEBUG_UNIT").first()
        if not inm:
            inm = Inmueble(alias="TEST_DEBUG_UNIT", tipo=TipoInmueble.DEPARTAMENTO, direccion="Test 123")
            session.add(inm)
            session.commit()
            
        prov = session.query(Proveedor).filter_by(nombre_entidad="TEST_DEBUG_PROV").first()
        if not prov:
            prov = Proveedor(nombre_entidad="TEST_DEBUG_PROV", categoria=CategoriaProveedor.SERVICIOS)
            session.add(prov)
            session.commit()
            
        obl = session.query(Obligacion).filter_by(inmueble_id=inm.id, proveedor_id=prov.id).first()
        if not obl:
            obl = Obligacion(inmueble_id=inm.id, proveedor_id=prov.id)
            session.add(obl)
            session.commit()
            
        # 2. Create Vencimiento
        ctrl = VencimientosController()
        
        # Cleanup previous run
        existing = session.query(Vencimiento).filter_by(obligacion_id=obl.id, periodo="12-2025").first()
        if existing:
            session.delete(existing)
            session.commit()
        
        data_create = {
            "obligacion_id": obl.id,
            "periodo": "12-2025",
            "fecha_vencimiento": date(2025, 12, 10),
            "monto_original": 1000.0,
            "estado": EstadoVencimiento.PENDIENTE
        }
        print("2. Creating Vencimiento (1000.0)...")
        ctrl.create_vencimiento(data_create)
        
        venc = session.query(Vencimiento).filter_by(obligacion_id=obl.id, periodo="12-2025").first()
        print(f"   Created ID: {venc.id}, Monto: {venc.monto_original}")
        
        # 3. Update as PAID with DIFFERENT amount
        # User pays 1200 instead of 1000
        data_update = {
            "estado": EstadoVencimiento.PAGADO.value, # "Pagado"
            "monto_original": 1000.0,
            "fecha_vencimiento": date(2025, 12, 10),
            "monto_pagado": 1200.0, # <--- THIS SHOULD BE SAVED
            "fecha_pago": date(2025, 12, 11)
        }
        
        print("3. Updating to PAGADO with monto_pagado=1200.0...")
        success = ctrl.update_vencimiento(venc.id, data_update)
        print(f"   Update success: {success}")
        
        # 4. Verify
        session.expire_all()
        venc = session.query(Vencimiento).filter_by(id=venc.id).first()
        
        print(f"4. Verifying... State: {venc.estado}")
        
        if not venc.pagos:
            print("   ERROR: No payment record found in 'venc.pagos'.")
        else:
            pago = venc.pagos[0]
            print(f"   Payment Found: {pago.monto}")
            if abs(pago.monto - 1200.0) < 0.01:
                print("   SUCCESS: Correct amount (1200.0) saved in Payment.")
            else:
                print(f"   FAILURE: Payment amount is {pago.monto}, expected 1200.0")

    except Exception as e:
        print(f"EXCEPTION: {e}")
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    reproduce_issue()
