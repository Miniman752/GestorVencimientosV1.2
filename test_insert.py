
import logging
from sqlalchemy import text
from database import init_db_engine, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestInsert")

def test_insertion():
    session = SessionLocal()
    candidates = ["OTRO", "OTROS", "Otro", "Otros", "SERVICIO", "SERVICIOS", "Servicio", "Servicios"]
    
    # Clean up first to avoid Unique Constraint on name
    try:
        session.execute(text("DELETE FROM proveedores WHERE nombre_entidad LIKE 'TestProv%'"))
        session.commit()
    except:
        session.rollback()

    valid_value = None

    for val in candidates:
        try:
            name = f"TestProv_{val}"
            logger.info(f"Testing value: '{val}'")
            # Raw Insert to bypass any SQLAlchemy ORM casting issues
            sql = text("INSERT INTO proveedores (nombre_entidad, categoria) VALUES (:n, :c)")
            session.execute(sql, {"n": name, "c": val})
            session.flush() # Should trigger error if invalid
            logger.info(f"✅ SUCCESS: '{val}' is valid.")
            valid_value = val
            session.rollback() # Don't actually keep it
            break 
        except Exception as e:
            logger.error(f"❌ FAILED: '{val}'. Error: {e}")
            session.rollback()

    if valid_value:
        print(f"FOUND VALID VALUE: {valid_value}")
    else:
        print("NO VALID VALUE FOUND IN CANDIDATES")
    
    session.close()

if __name__ == "__main__":
    from config import load_last_db_path
    last_db = load_last_db_path()
    if last_db:
        init_db_engine(last_db)
        test_insertion()
    else:
        print("No DB configured.")
