
import os
import sys

# Hack to find modules
sys.path.append(os.getcwd())

import config
from database import SessionLocal
from sqlalchemy import text

print(f"DEBUG: Using Database URL: {config.DATABASE_URL}")

session = SessionLocal()
try:
    tables = ["vencimientos", "obligaciones", "proveedores", "inmuebles"]
    
    with open("db_content_report.txt", "w", encoding="utf-8") as f:
        f.write(f"DB Content Report\n")
        f.write(f"URL: {config.DATABASE_URL}\n")
        f.write("--------------------------------\n")
        
        for t in tables:
            try:
                count = session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                f.write(f"Table '{t}': {count} records\n")
                
                if count > 0:
                    sample = session.execute(text(f"SELECT * FROM {t} LIMIT 1")).fetchall()
                    f.write(f"Sample {t}: {sample}\n")
            except Exception as e:
                f.write(f"Error checking {t}: {e}\n")

finally:
    session.close()
