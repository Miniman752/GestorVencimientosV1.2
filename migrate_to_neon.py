
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, make_transient
from sqlalchemy.schema import CreateTable
from pathlib import Path

import logging

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("migration.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

try:
    import psycopg2
    logging.info("psycopg2 module found.")
except ImportError:
    logging.error("ERROR: psycopg2 module not found. Please run: pip install psycopg2-binary")
    sys.exit(1)

from config import DB_PATH_STR, BASE_DIR
from models.entities import (
    Usuario, ProveedorServicio, Inmueble, PeriodoContable, YearConfig, 
    IndiceEconomico, AuditLog, Cotizacion, Obligacion, Credencial, 
    ReglaAjuste, Vencimiento, Pago
)
from database import Base

# --- CONFIGURATION ---
# Force local SQLite Source
SOURCE_DB_PATH = str(BASE_DIR / "vencimientos.db")
SOURCE_URL = f"sqlite:///{SOURCE_DB_PATH.replace(os.sep, '/')}"

# Target URL (Neon.tech)
DEST_URL = "postgresql://neondb_owner:npg_vhmWRL8ESXI3@ep-green-night-acbu7krn-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

logging.info(f"SOURCE: {SOURCE_URL}")
logging.info(f"DEST: {DEST_URL}")

def migrate():
    # 1. Setup Engines
    source_engine = create_engine(SOURCE_URL)
    dest_engine = create_engine(DEST_URL)

    # 2. Create Tables in Destination
    logging.info("Creating tables in destination...")
    # Base.metadata.drop_all(dest_engine) # OPTIONAL: Clean start
    Base.metadata.create_all(dest_engine)

    # 3. Setup Sessions
    SourceSession = sessionmaker(bind=source_engine)
    DestSession = sessionmaker(bind=dest_engine)
    
    source_session = SourceSession()
    dest_session = DestSession()

    # 4. Migration Order (Parents first to avoid FK constraint errors)
    # Note: Enum types must be handled carefully. SQLAlchemy usually creates them automatically.
    
    migration_order = [
        Usuario, 
        ProveedorServicio, 
        Inmueble, 
        PeriodoContable, 
        YearConfig, 
        IndiceEconomico, 
        AuditLog, 
        Cotizacion, 
        Obligacion, 
        Credencial, 
        ReglaAjuste, 
        Vencimiento, 
        Pago
    ]

    try:
        for model in migration_order:
            table_name = model.__tablename__
            logging.info(f"Migrating table: {table_name}...")
            
            # Fetch all records from source
            records = source_session.query(model).all()
            count = len(records)
            
            # Insert into destination
            for record in records:
                # Detach from source session
                source_session.expunge(record)
                make_transient(record) # Remove identity key -> Insert as new
                dest_session.add(record)
            
            dest_session.flush() # Send SQL to DB
            logging.info(f"Done. ({count} records)")
            
        dest_session.commit()
        logging.info("Migration completed successfully!")

    except Exception as e:
        logging.error(f"ERROR during migration: {e}")
        dest_session.rollback()
        import traceback
        logging.error(traceback.format_exc())
    finally:
        source_session.close()
        dest_session.close()

if __name__ == "__main__":
    print("Starting Migration to Neon.tech...")
    migrate()
