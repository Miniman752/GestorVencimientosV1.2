import sqlite3
import configparser
from pathlib import Path
import binascii

base_dir = Path("e:/43.Gestor de vencimientos/07.Gestor de vencimientos/src_restored")
config = configparser.ConfigParser()
config.read(base_dir / "config.ini")
db_path = config["General"]["last_db"]

print(f"Deep Inspecting DB: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n--- Raw Values Analysis ---")
    cursor.execute("SELECT id, estado FROM vencimientos")
    rows = cursor.fetchall()
    
    problem_count = 0
    possible_values = {'PENDIENTE', 'PAGADO', 'VENCIDO', 'REVISION'}
    
    for rid, estado in rows:
        if estado not in possible_values:
            problem_count += 1
            print(f"ID: {rid} | Val: {repr(estado)} | Hex: {binascii.hexlify(estado.encode('utf-8'))}")

    print(f"\nTotal problematic rows found: {problem_count}")
    
    # Try an update via Python iteration if SQL WHERE fails
    if problem_count > 0:
        print("\n--- Attempting Python-side Patch ---")
        updates = 0
        for rid, estado in rows:
            clean = estado.strip()
            new_val = None
            
            # Mapping logic
            if clean == "Pendiente": new_val = "PENDIENTE"
            elif clean == "Pagado": new_val = "PAGADO"
            elif clean == "Vencido": new_val = "VENCIDO"
            elif clean == "En Revision": new_val = "REVISION"
            elif clean == "Revision": new_val = "REVISION"
            
            if new_val:
                cursor.execute("UPDATE vencimientos SET estado = ? WHERE id = ?", (new_val, rid))
                updates += 1
                
        conn.commit()
        print(f"Python-side patched {updates} rows.")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
