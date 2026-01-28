import sqlite3
import configparser
from pathlib import Path

# Manual DB connection
base_dir = Path("e:/43.Gestor de vencimientos/07.Gestor de vencimientos/src_restored")
config = configparser.ConfigParser()
config.read(base_dir / "config.ini")
db_path = config["General"]["last_db"]

print(f"Patching DB: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Pendiente -> PENDIENTE
    cursor.execute("UPDATE vencimientos SET estado = 'PENDIENTE' WHERE estado = 'Pendiente'")
    print(f"Fixed Pendiente: {cursor.rowcount} rows")

    # 2. Pagado -> PAGADO
    cursor.execute("UPDATE vencimientos SET estado = 'PAGADO' WHERE estado = 'Pagado'")
    print(f"Fixed Pagado: {cursor.rowcount} rows")

    # 3. Vencido -> VENCIDO
    cursor.execute("UPDATE vencimientos SET estado = 'VENCIDO' WHERE estado = 'Vencido'")
    print(f"Fixed Vencido: {cursor.rowcount} rows")

    # 4. En Revision -> REVISION
    cursor.execute("UPDATE vencimientos SET estado = 'REVISION' WHERE estado = 'En Revision'")
    print(f"Fixed En Revision: {cursor.rowcount} rows")
    
    conn.commit()
    conn.close()
    print("Database patched successfully.")
    
except Exception as e:
    print(f"Error patching DB: {e}")
