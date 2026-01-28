from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.pool import QueuePool
import os
import inspect
from config import DATABASE_URL

# --- Global State ---
_engine = None
_SessionLocal = None
Base = declarative_base()

class SessionProxy:
    """
    Proxy to allow 'from database import SessionLocal' to work 
    even if the engine hasn't been initialized yet.
    """
    def __call__(self):
        if _SessionLocal is None:
            init_db_engine()
        return _SessionLocal()

SessionLocal = SessionProxy()

class EngineProxy:
    """    
    Proxy to allow 'from database import engine' to work.
    Forwards attribute access to the real engine.
    """
    def __getattr__(self, name):
        if _engine is None:
            init_db_engine()
        return getattr(_engine, name)
    
engine = EngineProxy()

def init_db_engine(db_url=None):
    """Initializes or Re-initializes the database engine."""
    global _engine, _SessionLocal
    
    url = db_url if db_url else DATABASE_URL
    
    # Ensure SQLite paths are absolute in frozen mode to prevent CWD ambiguity
    if url.startswith("sqlite:///") and "vencimientos.db" in url and getattr(sys, 'frozen', False):
        if not os.path.isabs(url.replace("sqlite:///", "")):
             # Re-construct absolute path based on BASE_DIR (which we fixed in config.py)
             from config import BASE_DIR
             url = f"sqlite:///{BASE_DIR / 'vencimientos.db'}"
             print(f"DEBUG: Fixed Frozen SQLite URL: {url}")
    
    # Dispose old if exists
    if _engine:
        # Check if it has dispose (real engine)
        if hasattr(_engine, 'dispose'):
            _engine.dispose()
        
    # FIX: Add check_same_thread=False for SQLite + GUI/Multi-threading
    connect_args = {}
    print(f"DEBUG: init_db_engine called. URL: {url}")
    if "sqlite" in url:
        connect_args = {'check_same_thread': False}
        _engine = create_engine(url, echo=False, connect_args=connect_args)
    else:
        # PostgreSQL / Neon Configuration for Stability
        # pool_pre_ping=True: Checks connection liveliness before usage, reconnects if dead.
        # pool_recycle=300: Recycles connections every 5 mins to prevent cloud timeout.
        _engine = create_engine(
            url, 
            echo=False, 
            pool_pre_ping=True, 
            pool_recycle=300, 
            pool_size=10, 
            max_overflow=20
        )
    # expire_on_commit=False is CRITICAL for GUI applications
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, expire_on_commit=False)

def run_migrations():
    """Runs simple migrations on existing database."""
    global _engine
    if not _engine: return

    try:
        with _engine.connect() as conn:
            # Check 1: ruta_comprobante_pago
            try:
                conn.execute(text("SELECT ruta_comprobante_pago FROM vencimientos LIMIT 1"))
            except Exception:
                conn.rollback() # Fix transaction abort state
                print("MIGRATION: Adding 'ruta_comprobante_pago' to 'vencimientos'...")
                try:
                    conn.execute(text("ALTER TABLE vencimientos ADD COLUMN ruta_comprobante_pago TEXT"))
                    conn.commit()
                except Exception as e: 
                    conn.rollback()
                    print(f"MIGRATION FAILED: {e}")

            # Check 2: documento_id
            try:
                conn.execute(text("SELECT documento_id FROM vencimientos LIMIT 1"))
            except Exception:
                conn.rollback() # Fix transaction abort state
                print("MIGRATION: Adding 'documento_id' column...")
                try:
                    conn.execute(text("ALTER TABLE vencimientos ADD COLUMN documento_id INTEGER"))
                    conn.commit()
                except Exception as e: 
                    conn.rollback()
                    print(f"MIGRATION FAILED (documento_id): {e}")

            # Check 3: comprobante_pago_id
            try:
                conn.execute(text("SELECT comprobante_pago_id FROM vencimientos LIMIT 1"))
            except Exception:
                conn.rollback() # Fix transaction abort state
                print("MIGRATION: Adding 'comprobante_pago_id' column...")
                try:
                    conn.execute(text("ALTER TABLE vencimientos ADD COLUMN comprobante_pago_id INTEGER"))
                    conn.commit()
                except Exception as e: 
                    conn.rollback()
                    print(f"MIGRATION FAILED (comprobante_pago_id): {e}")

            # Check 4: documento_id in PAGOS (NEW)
            try:
                conn.execute(text("SELECT documento_id FROM pagos LIMIT 1"))
            except Exception:
                conn.rollback()
                print("MIGRATION: Adding 'documento_id' to 'pagos'...")
                try:
                    conn.execute(text("ALTER TABLE pagos ADD COLUMN documento_id INTEGER"))
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f"MIGRATION FAILED (pagos.documento_id): {e}")
            
            # 2. Check Integrity (Unique Obligations)
            try:
                # SQLite doesn't support ADD CONSTRAINT easily. We use unique index.
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uk_obligacion_inmueble_servicio ON obligaciones(inmueble_id, servicio_id)"))
                
                # Phase 2: Performance Indexes for FKs
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_obligacion_inmueble ON obligaciones(inmueble_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_obligacion_servicio ON obligaciones(servicio_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pago_vencimiento ON pagos(vencimiento_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_regla_obligacion ON reglas_ajuste(obligacion_id)"))

                conn.commit()
            except Exception as e:
                print(f"MIGRATION INDEX INFO: {e}")

    except Exception as e:
        print(f"DB CHECK FAILED: {e}")

def get_db():
    # Helper that uses the proxy (which handles lazy init)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_new_db_file(path):
    """Creates a new empty database file and initializes schema."""
    url = f"sqlite:///{path}"
    temp_engine = create_engine(url)
    
    # Import models to ensure they are registered in Base
    # We must ensure models are imported somewhere in the app before this runs.
    # Usually main_window imports controllers which import models.
    from models.entities import Inmueble, Obligacion, Vencimiento, Pago, IndiceEconomico
    
    Base.metadata.create_all(bind=temp_engine)
    temp_engine.dispose()
    return True

def init_db(db_url=None):
    """Initializes or Re-initializes the database engine."""
    caller = inspect.stack()[1]
    print(f"DEBUG: init_db called from {caller.filename}:{caller.lineno} in {caller.function}")
    init_db_engine(db_url)
    
    # Importar modelos para que SQLAlchemy los reconozca al crear tablas
    # This is crucial for create_all to see them
    from models.entities import Inmueble, Obligacion, Vencimiento, Pago, IndiceEconomico, PeriodoContable, YearConfig
    
    # Create tables first (if they don't exist)
    print(f"DEBUG: Creating tables. Registered models: {Base.metadata.tables.keys()}")
    Base.metadata.create_all(bind=engine) # Changed _engine to engine
    
    # Run Migrations (Manual Updates)
    run_migrations()

    # Seed data if empty
    from seed_data import seed
    seed()