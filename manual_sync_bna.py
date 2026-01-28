import sys
import datetime
from database import SessionLocal
from models.entities import Cotizacion, Moneda
from services.bna_service import BnaService

def test_sync():
    print("--- Diagnosticando Sincronización BNA ---")
    
    # 1. Check Connectivity
    print("\n[1] Verificando conexión a Internet...")
    if not BnaService.check_connectivity():
        print("ERROR: No hay conexión a internet.")
        return

    print("OK.")

    # 2. Check Existing Data
    print("\n[2] Verificando Base de Datos local...")
    session = SessionLocal()
    try:
        existing = session.query(Cotizacion).filter(Cotizacion.moneda == Moneda.USD).all()
        existing_dates = {c.fecha for c in existing}
        print(f"Registros existentes de USD: {len(existing)}")
        if existing:
            sorted_dates = sorted(list(existing_dates), reverse=True)
            print(f"Última fecha registrada: {sorted_dates[0]}")
            print(f"Últimos 5 registros: {[str(d) for d in sorted_dates[:5]]}")
        else:
            print("No hay registros de USD.")
    except Exception as e:
        print(f"ERROR leyendo DB: {e}")
        return

    # 3. Check BNA API
    print("\n[3] Consultando API BNA (ArgentinaDatos)...")
    history = BnaService.fetch_history()
    if not history:
        print("ERROR: La API no retornó datos.")
        return
    print(f"Registros obtenidos de la API: {len(history)}")
    print(f"Último registro API: {history[0]['fecha']}")

    # 4. Simulate Sync
    print("\n[4] Simulando Sincronización...")
    to_insert = 0
    possible_updates = []
    
    for item in history:
        if item['fecha'] not in existing_dates:
            to_insert += 1
            possible_updates.append(item['fecha'])
    
    print(f"Fechas Faltantes (Huecos) detectados: {to_insert}")
    if to_insert > 0:
        print(f"Ejemplos de fechas a insertar: {[str(d) for d in possible_updates[:5]]}")
    else:
        print("RESULTADO: Tu base de datos ya está completa o tiene registros para todas las fechas que provee la API.")
        print("NOTA: El sistema NO sobrescribe datos existentes (como cotizaciones Blue manuales).")

if __name__ == "__main__":
    test_sync()
