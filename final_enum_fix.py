import sqlite3
import configparser
from pathlib import Path

base_dir = Path("e:/43.Gestor de vencimientos/07.Gestor de vencimientos/src_restored")
config = configparser.ConfigParser()
config.read(base_dir / "config.ini")
db_path = config["General"]["last_db"]

print(f"Force Patching DB: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Force generic update
    cursor.execute("UPDATE vencimientos SET estado = 'PENDIENTE' WHERE estado LIKE 'Pendiente'")
    print(f"Fixed Pendiente: {cursor.rowcount}")
    
    cursor.execute("UPDATE vencimientos SET estado = 'PAGADO' WHERE estado LIKE 'Pagado'")
    print(f"Fixed Pagado: {cursor.rowcount}")
    
    cursor.execute("UPDATE vencimientos SET estado = 'VENCIDO' WHERE estado LIKE 'Vencido'")
    print(f"Fixed Vencido: {cursor.rowcount}")
    
    cursor.execute("UPDATE vencimientos SET estado = 'REVISION' WHERE estado LIKE '%Revision%' AND estado != 'REVISION'")
    print(f"Fixed Revision: {cursor.rowcount}")
    
    conn.commit()
    conn.close()
    print("Patch complete.")
    
except Exception as e:
    print(e)
