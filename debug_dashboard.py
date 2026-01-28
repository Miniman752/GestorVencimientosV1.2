
import sys
import os

# Set up path to project root
project_root = r"e:\44.Gestos Vencimientos (PostgreSQL)"
if project_root not in sys.path:
    sys.path.append(project_root)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Correct import based on file structure
from database import get_db, SessionLocal, init_db_engine

def debug_data():
    # Ensure engine is initialized
    init_db_engine()
    
    session = SessionLocal()
    try:
        print("--- DEBUGGING DASHBOARD DATA ---")
        
        # 1. Check raw Vencimientos count
        res = session.execute(text("SELECT COUNT(*) FROM vencimientos")).scalar()
        print(f"Total Vencimientos: {res}")

        # 2. Check Vencimientos linked to Obligaciones
        res = session.execute(text("SELECT COUNT(*) FROM vencimientos v JOIN obligaciones o ON v.obligacion_id = o.id")).scalar()
        print(f"Vencimientos with Valid Obligaciones: {res}")
        
        # 3. Check Vencimientos -> Obligaciones -> Proveedores
        res = session.execute(text("""
            SELECT COUNT(*) 
            FROM vencimientos v 
            JOIN obligaciones o ON v.obligacion_id = o.id
            JOIN proveedores p ON o.servicio_id = p.id
        """)).scalar()
        print(f"Vencimientos with Valid Proveedores: {res}")

        # 4. Inspect Categories (Raw)
        print("\n--- CATEGORY RAW DATA ---")
        res = session.execute(text("""
            SELECT p.id, p.nombre_entidad, p.categoria 
            FROM proveedores p 
            LIMIT 10
        """)).fetchall()
        for r in res:
            print(f"Prov: {r[1]} | Cat: {r[2]}")
            
        # 4b. Inspect Distinct Categories
        print("\n--- DISTINCT CATEGORIES ---")
        res = session.execute(text("SELECT DISTINCT categoria FROM proveedores")).fetchall()
        for r in res:
            print(f"Distinct Cat: {r[0]}")

        # 5. Run the Problematic Query
        print("\n--- PROBLEMATIC QUERY TEST ---")
        cat_query = text("""
            SELECT COALESCE(p.categoria, 'OTRO'), SUM(v.monto_original)
            FROM vencimientos v
            JOIN obligaciones o ON v.obligacion_id = o.id
            LEFT JOIN proveedores p ON o.servicio_id = p.id
            WHERE v.is_deleted = 0 AND v.estado != 'PAGADO'
            GROUP BY COALESCE(p.categoria, 'OTRO')
            ORDER BY SUM(v.monto_original) DESC
        """)
        cat_stats = session.execute(cat_query).fetchall()
        print(f"Query Result Count: {len(cat_stats)}")
        for r in cat_stats:
            print(f"Cat: {r[0]} | Amount: {r[1]}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_data()
