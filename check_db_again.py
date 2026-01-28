import sqlite3
import configparser
from pathlib import Path

base_dir = Path("e:/43.Gestor de vencimientos/07.Gestor de vencimientos/src_restored")
config = configparser.ConfigParser()
config.read(base_dir / "config.ini")
db_path = config["General"]["last_db"]

print(f"Checking DB: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT estado FROM vencimientos")
    rows = cursor.fetchall()
    print("Values found in DB:")
    for r in rows:
        print(f"'{r[0]}'")
    conn.close()
except Exception as e:
    print(e)
