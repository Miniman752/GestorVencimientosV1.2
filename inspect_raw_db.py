import sqlite3
import os
import configparser
from pathlib import Path

def check_raw_values():
    # Attempt to read config.ini
    config_path = Path("config.ini")
    db_path = "vencimientos.db" # Default
    
    if config_path.exists():
        config = configparser.ConfigParser()
        config.read(config_path)
        if "General" in config and "last_db" in config["General"]:
             db_path = config["General"]["last_db"]
    
    print(f"Checking DB at: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"DB file not found at {db_path}")
        # Try finding in current dir if path was absolute but wrong context
        local_db = "vencimientos.db"
        if os.path.exists(local_db):
            print(f"Fallback: Checking {local_db}")
            db_path = local_db
        else:
            return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Inmuebles Raw States ---")
    try:
        cursor.execute("SELECT id, alias, estado FROM inmuebles LIMIT 5")
        for row in cursor.fetchall():
            print(row)
    except Exception as e:
        print(e)
        
    conn.close()

if __name__ == "__main__":
    check_raw_values()
