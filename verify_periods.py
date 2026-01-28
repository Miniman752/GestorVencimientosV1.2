import sys
import os
from datetime import date
from database import SessionLocal, init_db
from models.entities import Vencimiento, Obligacion, EstadoVencimiento
from services.vencimiento_service import VencimientoService
from controllers.vencimientos_controller import VencimientosController

# Seteo básico
init_db()
session = SessionLocal()
service = VencimientoService()
controller = VencimientosController()

def run_verification():
    print("--- INICIANDO VERIFICACIÓN DE PERIODOS ---")
    
    # 1. Obtener una Obligación existente para usar de prueba
    obl = session.query(Obligacion).first()
    if not obl:
        print("❌ CRÍTICO: No hay obligaciones en la base de datos para probar.")
        return
    
    print(f"✅ Usando Obligación ID {obl.id} ({obl.inmueble.alias} - {obl.proveedor.nombre_entidad})")

    # 2. Definir dos periodos de prueba
    period_a = "2026-05"
    date_a = date(2026, 5, 10)
    
    period_b = "2026-06"
    date_b = date(2026, 6, 15)

    # 3. Crear Vencimiento en Periodo A
    print(f"\n[PRUEBA 1] Creando Vencimiento en {period_a}...")
    data_a = {
        "obligacion_id": obl.id,
        "periodo": period_a,
        "fecha_vencimiento": date_a,
        "monto_original": 1500.00,
        "estado": EstadoVencimiento.PENDIENTE,
        "ruta_archivo_pdf": None,
        "ruta_comprobante_pago": None
    }
    
    try:
        controller.create_vencimiento(data_a)
        print("✅ Creación exitosa (Controller no arrojó error).")
    except Exception as e:
        print(f"❌ Error creando en Periodo A: {e}")
        return

    # 4. Crear Vencimiento en Periodo B
    print(f"\n[PRUEBA 2] Creando Vencimiento en {period_b}...")
    data_b = {
        "obligacion_id": obl.id,
        "periodo": period_b,
        "fecha_vencimiento": date_b,
        "monto_original": 2500.00,
        "estado": EstadoVencimiento.PENDIENTE,
        "ruta_archivo_pdf": None,
        "ruta_comprobante_pago": None
    }
    
    try:
        controller.create_vencimiento(data_b)
        print("✅ Creación exitosa.")
    except Exception as e:
        print(f"❌ Error creando en Periodo B: {e}")

    # 5. Verificar Persistencia y Filtrado
    print(f"\n[PRUEBA 3] Verificando Filtrado por Periodo...")
    
    # Check Period A
    recs_a, _ = controller.get_all_vencimientos(period_id=period_a, limit=100)
    found_a = any(v.monto_original == 1500.00 and v.fecha_vencimiento == date_a for v in recs_a)
    
    if found_a:
        print(f"✅ Periodo {period_a}: Registro encontrado correctamente.")
    else:
        print(f"❌ Periodo {period_a}: NO se encontró el registro creado.")

    # Check Period B
    recs_b, _ = controller.get_all_vencimientos(period_id=period_b, limit=100)
    found_b = any(v.monto_original == 2500.00 and v.fecha_vencimiento == date_b for v in recs_b)
    
    if found_b:
        print(f"✅ Periodo {period_b}: Registro encontrado correctamente.")
    else:
        print(f"❌ Periodo {period_b}: NO se encontró el registro creado.")

    # Cross Check: Ensure A is not in B
    leak = any(v.monto_original == 1500.00 for v in recs_b)
    if not leak:
        print("✅ Aislamiento correcto: El registro de Mayo no aparece en Junio.")
    else:
        print("❌ ERROR DE FILTRADO: El registro de Mayo APARECE en Junio.")

    # 6. Database Check (Direct Query)
    print("\n[PRUEBA 4] Verificación Directa en DB...")
    db_rec_a = session.query(Vencimiento).filter_by(periodo=period_a, monto_original=1500.00).first()
    if db_rec_a:
        print(f"✅ DB Persistencia OK para {period_a}. ID Generado: {db_rec_a.id}")
        # Clean up
        print("🧹 Limpiando datos de prueba...")
        session.delete(db_rec_a)
        
        db_rec_b = session.query(Vencimiento).filter_by(periodo=period_b, monto_original=2500.00).first()
        if db_rec_b:
            session.delete(db_rec_b)
        
        session.commit()
        print("✅ Limpieza completada.")
    else:
        print(f"❌ FATAL: El registro no existe en la base de datos física.")

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        print(f"❌ Excepción General: {e}")
