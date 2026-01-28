import sqlite3
import configparser
from pathlib import Path

# Manual DB connection to bypass SQLAlchemy mapping
base_dir = Path("e:/43.Gestor de vencimientos/07.Gestor de vencimientos/src_restored")
config = configparser.ConfigParser()
config.read(base_dir / "config.ini")
db_path = config["General"]["last_db"]

print(f"Inspecting DB: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n--- Distinct States in 'vencimientos' table ---")
    cursor.execute("SELECT DISTINCT estado FROM vencimientos")
    rows = cursor.fetchall()
    for row in rows:
        print(f"'{row[0]}'")
        
    print("\n--- Listing first 5 rows ---")
    cursor.execute("SELECT id, estado FROM vencimientos LIMIT 5")
    for row in rows:
        print(row)
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
