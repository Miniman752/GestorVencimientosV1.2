import sys
import os
from sqlalchemy import create_engine, text
from config import DATABASE_URL

# Define checks
CHECKS = [
    {
        "name": "Duplicidad de Vencimientos (Mismo Periodo y Obligacion)",
        "query": """
            SELECT obligacion_id, periodo, COUNT(*) as count
            FROM vencimientos
            GROUP BY obligacion_id, periodo
            HAVING COUNT(*) > 1
        """
    },
    {
        "name": "Duplicidad de Proveedores (Mismo Nombre)",
        "query": """
            SELECT nombre_entidad, COUNT(*) as count
            FROM proveedores
            GROUP BY nombre_entidad
            HAVING COUNT(*) > 1
        """
    },
    {
        "name": "Duplicidad de Inmuebles (Mismo Alias)",
        "query": """
            SELECT alias, COUNT(*) as count
            FROM inmuebles
            GROUP BY alias
            HAVING COUNT(*) > 1
        """
    }
]

def run_checks(db_name, db_url):
    print(f"\n{'='*60}")
    print(f"ANÁLISIS DE BASE DE DATOS: {db_name}")
    print(f"URL: {db_url}")
    print(f"{'='*60}")
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            for check in CHECKS:
                print(f"\n[CHECK] {check['name']}...")
                try:
                    result = conn.execute(text(check['query'])).fetchall()
                    if result:
                        print(f"   ❌ SE ENCONTRARON {len(result)} CASOS:")
                        for row in result:
                            print(f"      -> {row}")
                    else:
                        print("   ✅ Sin duplicados.")
                except Exception as e:
                    print(f"   ⚠️ Error ejecutando query (posible diferencia de esquema): {e}")
                    
    except Exception as e:
        print(f"CRITICAL ERROR CONNECTING TO {db_name}: {e}")

if __name__ == "__main__":
    # 1. Check PostgreSQL (Current Config)
    run_checks("POSTGRESQL (Producción)", DATABASE_URL)
    
    # 2. Check Local SQLite
    local_db_path = os.path.join(os.getcwd(), "vencimientos.db")
    if os.path.exists(local_db_path):
        run_checks("LOCAL (SQLite Backup)", f"sqlite:///{local_db_path}")
    else:
        print("\n\n [INFO] No se encontró base local 'vencimientos.db'.")
