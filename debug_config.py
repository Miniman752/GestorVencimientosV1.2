import configparser
from pathlib import Path
import os
import sys

BASE_DIR = Path("e:/43.Gestor de vencimientos/07.Gestor de vencimientos/src_restored")
CONFIG_FILE = BASE_DIR / "config.ini"

print(f"Checking config file: {CONFIG_FILE}")
print(f"Exists: {CONFIG_FILE.exists()}")

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
print(f"Sections: {config.sections()}")

if "General" in config:
    print("General section found")
    last_db = config["General"].get("last_db")
    print(f"Raw last_db: '{last_db}'")
    
    if last_db:
        exists = os.path.exists(last_db)
        print(f"os.path.exists('{last_db}'): {exists}")
    else:
        print("last_db is empty or None")
else:
    print("General section MISSING")
