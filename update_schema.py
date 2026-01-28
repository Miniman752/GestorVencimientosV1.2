
import sqlalchemy
from sqlalchemy import create_engine, text
from config import DATABASE_URL
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_schema():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        
        # 1. Create Documentos Table
        logger.info("Checking 'documentos' table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS documentos (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    file_data BYTEA NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    mime_type VARCHAR(100),
                    file_size INTEGER
                );
            """))
            logger.info("Table 'documentos' ensured.")
        except Exception as e:
            logger.error(f"Error creating table: {e}")

        # 2. Add Columns to Vencimientos
        logger.info("Checking columns in 'vencimientos'...")
        try:
            # Check if column exists
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='vencimientos' AND column_name='documento_id';"))
            if not result.fetchone():
                logger.info("Adding 'documento_id' to vencimientos...")
                conn.execute(text("ALTER TABLE vencimientos ADD COLUMN documento_id INTEGER REFERENCES documentos(id);"))
            
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='vencimientos' AND column_name='comprobante_pago_id';"))
            if not result.fetchone():
                logger.info("Adding 'comprobante_pago_id' to vencimientos...")
                conn.execute(text("ALTER TABLE vencimientos ADD COLUMN comprobante_pago_id INTEGER REFERENCES documentos(id);"))
                
        except Exception as e:
            logger.error(f"Error altering vencimientos: {e}")

        # 3. Add Columns to Pagos
        logger.info("Checking columns in 'pagos'...")
        try:
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='pagos' AND column_name='documento_id';"))
            if not result.fetchone():
                logger.info("Adding 'documento_id' to pagos...")
                conn.execute(text("ALTER TABLE pagos ADD COLUMN documento_id INTEGER REFERENCES documentos(id);"))
        except Exception as e:
            logger.error(f"Error altering pagos: {e}")

        # 4. Add Columns to Cotizaciones
        logger.info("Checking columns in 'cotizaciones'...")
        try:
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='cotizaciones' AND column_name='compra';"))
            if not result.fetchone():
                logger.info("Adding 'compra' to cotizaciones...")
                conn.execute(text("ALTER TABLE cotizaciones ADD COLUMN compra FLOAT;"))
        except Exception as e:
            logger.error(f"Error altering cotizaciones: {e}")
            
    logger.info("Schema update complete.")

if __name__ == "__main__":
    update_schema()
