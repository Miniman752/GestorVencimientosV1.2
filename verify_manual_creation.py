
import sys
import os
from pathlib import Path

# Fix Path
BASE_DIR = Path(r"e:\44.Gestos Vencimientos (PostgreSQL)")
sys.path.append(str(BASE_DIR))

from datetime import date
from models.entities import CategoriaServicio, EstadoVencimiento, TipoPropiedad, RolUsuario
from services.catalogs_service import CatalogService, ObligacionService
from services.vencimiento_service import VencimientoService, VencimientoCreateDTO
from services.auth_service import AuthService
from database import SessionLocal

def verify_manual_creation():
    print("--- INICIANDO VERIFICACIÓN DE CREACIÓN MANUAL ---")
    session = SessionLocal()
    try:
        # 1. Create Inmueble (Manual)
        cat_service = CatalogService()
        print("\n[1] Creando Inmueble...")
        try:
            from dtos.catalogs import InmuebleCreateDTO
            inm_dto = InmuebleCreateDTO(
                alias="Test Office 2026",
                direccion="Fake St 123",
                tipo_propiedad=TipoPropiedad.OFICINA
            )
            cat_service.create_inmueble(inm_dto)
            # Fetch back
            inm = cat_service.get_inmuebles()[-1]
            print(f"✅ Inmueble creado: ID {inm.id} - {inm.alias}")
        except Exception as e:
            print(f"❌ Error creando Inmueble: {e}")
            return

        # 2. Create Proveedor (Manual)
        print("\n[2] Creando Proveedor...")
        try:
            from dtos.catalogs import ProveedorCreateDTO
            prov_dto = ProveedorCreateDTO(
                nombre_entidad="Servicios Test SA",
                categoria=CategoriaServicio.SERVICIO,
                frecuencia_defecto="Mensual"
            )
            cat_service.create_proveedor(prov_dto)
            prov = cat_service.get_proveedores()[-1]
            print(f"✅ Proveedor creado: ID {prov.id} - {prov.nombre_entidad}")
        except Exception as e:
            print(f"❌ Error creando Proveedor: {e}")
            return

        # 3. Create Obligacion (Link)
        print("\n[3] Vinculando (Obligación)...")
        obl_service = ObligacionService()
        try:
            obl_data = {
                "inmueble_id": inm.id,
                "proveedor_id": prov.id,
                "identificador_cliente": "CLI-999"
            }
            obl_service.create(obl_data)
            # Find it
            from models.entities import Obligacion
            obl = session.query(Obligacion).filter_by(inmueble_id=inm.id, proveedor_id=prov.id).first()
            print(f"✅ Obligación creada: ID {obl.id}")
        except Exception as e:
            print(f"❌ Error creando Obligación: {e}")
            return

        # 4. Create Vencimiento (Manual Form Simulation)
        print("\n[4] Creando Vencimiento (Simulación Form)...")
        venc_service = VencimientoService()
        try:
            venc_dto = VencimientoCreateDTO(
                obligacion_id=obl.id,
                periodo="2026-01",
                fecha_vencimiento=date(2026, 1, 15),
                monto_original=15000.50,
                estado=EstadoVencimiento.PENDIENTE
            )
            venc_service.create(venc_dto)
            print(f"✅ Vencimiento creado para Obligación {obl.id}")
        except Exception as e:
            print(f"❌ Error creando Vencimiento: {e}")
            return

        # 5. Create User (Auth)
        print("\n[5] Creando Usuario Operador...")
        try:
            AuthService.create_user(
                username=f"user_test_{date.today()}", 
                password="password123",
                role=RolUsuario.OPERADOR
            )
            print("✅ Usuario Operador creado exitosamente.")
        except ValueError:
            print("⚠️ Usuario ya existe (OK).")
        except Exception as e:
             print(f"❌ Error creando Usuario: {e}")

        print("\n✅ TODAS LAS PRUEBAS DE CREACIÓN PASARON.")

    except Exception as ie:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL FAILURE: {ie}")
    finally:
        session.close()

if __name__ == "__main__":
    verify_manual_creation()
