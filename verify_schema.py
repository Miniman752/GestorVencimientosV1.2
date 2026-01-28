from database import SessionLocal
from sqlalchemy import text
import sys

from services.migration_service import MigrationService

def verify():
    print("Running Migrations...")
    MigrationService.run_startup_migrations()
    
    try:
        db = SessionLocal()
        result = db.execute(text("PRAGMA table_info(pagos)")).fetchall()
        columns = [row[1] for row in result]
        print(f"Columns in pagos: {columns}")
        
        if 'monto' in columns:
            print("SUCCESS: 'monto' column found.")
            sys.exit(0)
        else:
            print("FAILURE: 'monto' column NOT found.")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify()
