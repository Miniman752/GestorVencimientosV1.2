from database import SessionLocal
from sqlalchemy import text
from models.entities import Vencimiento, PeriodoContable

def inspect_data():
    db = SessionLocal()
    try:
        print("--- Periodos Contables ---")
        periods = db.query(PeriodoContable).limit(5).all()
        for p in periods:
            print(f"ID: {p.periodo_id} | Est: {p.estado}")

        print("\n--- Vencimientos ---")
        vencs = db.query(Vencimiento).limit(5).all()
        for v in vencs:
            # Assuming 'periodo' column exists or is inferred from date?
            # Model definition step 308 didn't show Vencimiento model fully.
            # Let's check entities.py or just print properties
            print(f"ID: {v.id} | Periodo: {getattr(v, 'periodo', 'N/A')} | Fecha: {v.fecha_vencimiento}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_data()
