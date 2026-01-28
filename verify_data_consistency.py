import os
from sqlalchemy import create_engine, text
from config import DATABASE_URL
import re

def verify_consistency():
    print(f"VERIFICANDO CONSISTENCIA DE DATOS EN: {DATABASE_URL}")
    print("-" * 60)
    
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # 1. Check Period Format (YYYY-MM)
        print("\n[1] Verificando Formato de Periodos (Esperado: YYYY-MM)...")
        query_bad_periods = text("SELECT id, period FROM vencimientos WHERE periodo !~ '^\d{4}-\d{2}$'")
        # Postgres regex operator ~ 
        # Wait, table column is 'periodo' or 'period'? Screenshot says 'periodo'. 
        # My previous code used 'periodo'. Let's check schema/previous errors if any. 
        # verify_duplicates.py used 'periodo'. OK.
        
        try:
             # Check for any row where format is NOT YYYY-MM
             # Note: Postgres regex is slightly different syntax sometimes, strictly '^\d{4}-\d{2}$'
             q = text("SELECT id, periodo FROM vencimientos WHERE periodo !~ '^[0-9]{4}-[0-9]{2}$'")
             bad_periods = conn.execute(q).fetchall()
             
             if bad_periods:
                 print(f"   ❌ ALERTA: Se encontraron {len(bad_periods)} periodos con formato incorrecto:")
                 for row in bad_periods:
                     print(f"      ID: {row[0]}, Valor: '{row[1]}'")
             else:
                 print("   ✅ Todos los periodos tienen formato correcto (YYYY-MM).")
                 
        except Exception as e:
            print(f"   ⚠️ Error verificando periodos: {e}")

        # 2. Check Moneda Consistency
        print("\n[2] Verificando Monedas...")
        try:
            q_currencies = text("SELECT DISTINCT moneda FROM vencimientos")
            currencies = conn.execute(q_currencies).fetchall()
            print(f"   ℹ️ Monedas encontradas: {[c[0] for c in currencies]}")
        except Exception as e:
             print(f"   ⚠️ Error verificando monedas: {e}")

        # 3. Check for Orphaned Obligations (Vencimientos pointing to non-existent Obligacion)
        print("\n[3] Verificando Integridad Referencial (Vencimientos -> Obligaciones)...")
        try:
            q_orphans = text("""
                SELECT v.id, v.obligacion_id 
                FROM vencimientos v 
                LEFT JOIN obligaciones o ON v.obligacion_id = o.id 
                WHERE o.id IS NULL
            """)
            orphans = conn.execute(q_orphans).fetchall()
            if orphans:
                 print(f"   ❌ ALERTA: {len(orphans)} vencimientos huérfanos (sin obligación válida).")
            else:
                 print("   ✅ Integridad referencial correcta.")
        except Exception as e:
            print(f"   ⚠️ Error verificando integridad: {e}")

if __name__ == "__main__":
    import sys
    # Redirect stdout to file
    with open("consistency_result.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        verify_consistency()
        sys.stdout = sys.__stdout__
    
    # Also print to console for backup
    with open("consistency_result.txt", "r", encoding="utf-8") as f:
        print(f.read())
