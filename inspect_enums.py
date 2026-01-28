
import sys
import logging
from sqlalchemy import text
from database import init_db_engine, SessionLocal

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Inspector")

def check_enums():
    # Connect
    session = SessionLocal()
    try:
        # 1. Inspect Distinct Values in Table (if any)
        result = session.execute(text("SELECT DISTINCT categoria FROM proveedores"))
        rows = result.fetchall()
        logger.info(f"Existing Categories in DB Table: {[r[0] for r in rows]}")

        # 2. Inspect Enum Definition in Postgres
        # This query gets enum labels for type 'categoriaservicio'
        sql_enum = """
            SELECT e.enumlabel
            FROM pg_type t 
            JOIN pg_enum e ON t.oid = e.enumtypid  
            WHERE t.typname = 'estadovencimiento';
        """
        result_enum = session.execute(text(sql_enum))
        labels = [r[0] for r in result_enum.fetchall()]
        logger.info(f"Allowed ENUM Labels in Postgres: {labels}")

    except Exception as e:
        logger.error(f"Error inspecting: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    from config import load_last_db_path
    last_db = load_last_db_path()
    if last_db:
        init_db_engine(last_db)
        check_enums()
    else:
        print("No DB configured.")
