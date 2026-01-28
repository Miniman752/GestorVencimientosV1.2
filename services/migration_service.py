
from database import SessionLocal
from models.entities import Obligacion, ReglaAjuste, TipoAjuste
from utils.logger import app_logger

class MigrationService:
    @staticmethod
    def run_startup_migrations():
        """
        Runs ad-hoc migrations to ensure data consistency on startup.
        """
        try:
            db = SessionLocal()
            # MIGRATION: Auto-assign logic to existing obligations
            obligations = db.query(Obligacion).all()
            count = 0
            for obligation in obligations:
                if not obligation.reglas_ajuste:
                    app_logger.info(f"Migrando Obligacion {obligation.id} -> Estacional+IPC")
                    new_rule = ReglaAjuste(
                        obligacion_id=obligation.id,
                        tipo_ajuste=TipoAjuste.ESTACIONAL_IPC.value, # Fix: Use .value
                        frecuencia_meses=1
                    )
                    db.add(new_rule)
                    count += 1
            if count > 0:
                db.commit()
                app_logger.info(f"Migración Completada: {count} reglas creadas.")
            
            # MIGRATION: Schema Update (Add 'monto' to 'pagos')
            try:
                from sqlalchemy import text, inspect
                
                inspector = inspect(db.get_bind())
                columns = [c['name'] for c in inspector.get_columns('pagos')]
                
                if 'monto' not in columns:
                    app_logger.info("Migración Schema: Agregando columna 'monto' a tabla 'pagos'...")
                    db.execute(text("ALTER TABLE pagos ADD COLUMN monto DECIMAL(15, 2)"))
                    db.commit()
                    app_logger.info("Migración Schema Completada.")
            except Exception as e:
                # Log but don't crash, might be permissions or other DB type
                app_logger.error(f"Error migrando Schema Pagos: {e}")

            db.close()
        except Exception as e:
            app_logger.error(f"Error en migración: {e}")
