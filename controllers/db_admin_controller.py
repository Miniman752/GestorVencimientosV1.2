import os
import shutil
import sqlite3
import pandas as pd
from datetime import datetime
from config import DB_NAME, DATABASE_URL, get_backup_dir, set_backup_dir, get_admin_password
from database import SessionLocal
from models.entities import Obligacion, ReglaAjuste, TipoAjuste, CategoriaServicio

from utils.logger import app_logger
import subprocess
import platform

class DbAdminController:
    def __init__(self):
        # Determine actual DB path from DATABASE_URL
        self.db_url = DATABASE_URL
        self.is_cloud = "postgres" in self.db_url or "neon.tech" in self.db_url
        
        if self.is_cloud:
            self.db_path = self.db_url # Not a file path
        else:
             self.db_path = DATABASE_URL.replace("sqlite:///", "") 
             
        self.backup_dir = get_backup_dir()
        
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)

    def set_custom_backup_path(self, path):
        """Updates the backup path in config and controller."""
        set_backup_dir(path)
        self.backup_dir = split_path = get_backup_dir() # Reload to be sure
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        return True, "Ruta actualizada correctamente."

    def create_quick_backup(self):
        """
        Creates a lightweight JSON backup of critical data.
        Much faster than Excel export for exit routine.
        """
        import json
        import gzip
        from datetime import datetime
        from models.entities import Vencimiento, Pago, Obligacion, Inmueble, ProveedorServicio
        from database import SessionLocal
        from datetime import date
        
        session = SessionLocal()
        try:
            data = {}
            
            # Helper: Row to Dict
            def to_dict(obj):
                d = {}
                for c in obj.__table__.columns:
                     val = getattr(obj, c.name)
                     if isinstance(val, (date, datetime)):
                         val = val.isoformat()
                     elif hasattr(val, "value"): # Handle Enums
                         val = val.value
                     d[c.name] = val
                return d

            # 1. Vencimientos
            vencs = session.query(Vencimiento).all()
            data["vencimientos"] = [to_dict(x) for x in vencs]
            
            # 2. Pagos
            pagos = session.query(Pago).all()
            data["pagos"] = [to_dict(x) for x in pagos]
            
            # 3. Obligaciones (Critical Config)
            obs = session.query(Obligacion).all()
            data["obligaciones"] = [to_dict(x) for x in obs]
            
            # 4. Inmuebles
            inms = session.query(Inmueble).all()
            data["inmuebles"] = [to_dict(x) for x in inms]

            # 5. Proveedores
            provs = session.query(ProveedorServicio).all()
            data["proveedores"] = [to_dict(x) for x in provs]
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            filename = f"SIGV_QuickBackup_{timestamp}.json.gz"
            final_path = self.backup_dir / filename
            
            # Ensure dir
            if not self.backup_dir.exists():
                self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            with gzip.open(final_path, 'wt', encoding='utf-8') as f:
                json.dump(data, f)
                
            return str(final_path)
            
        except Exception as e:
            app_logger.error(f"Error creating quick backup: {e}")
            return None
        finally:
            session.close()

    def open_backup_folder(self):
        """Opens the backup directory in the OS file explorer."""
        path = str(self.backup_dir)
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            return True, "Carpeta abierta."
        except Exception as e:
            app_logger.error(f"Error opening folder: {e}")
            return False, f"No se pudo abrir la carpeta: {e}"

    def create_backup(self, custom_dest=None):
        """Creates a timestamped copy of the database. 
        If custom_dest is provided (Path object), copies there instead of default backup path."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            backup_filename = f"SIGV_Backup_{timestamp}.db"
            
            target_dir = custom_dest if custom_dest else self.backup_dir
             
            # Ensure target exists
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)

            if self.is_cloud:
                # Cloud Backup -> Export to Excel/Dump
                backup_filename = f"SIGV_CloudBackup_{timestamp}.xlsx"
                backup_path = target_dir / backup_filename
                success, msg = self.export_to_excel_full(str(backup_path))
                if not success: raise Exception(msg)
            else:
                # Local Backup -> File Copy
                backup_filename = f"SIGV_Backup_{timestamp}.db"
                backup_path = target_dir / backup_filename
                shutil.copy2(self.db_path, backup_path)
                
            app_logger.info(f"Backup created: {backup_path}")
            return True, f"Backup created successfully: {os.path.basename(backup_path)}"
        except Exception as e:
            app_logger.error(f"Backup failed: {e}")
            return False, str(e)

    def restore_database(self, backup_path, password):
        """Restores the database from a backup file."""
        if self.is_cloud:
            return False, "La restauración automática no está disponible en modo Nube/Postgres.\nContacte a soporte para importar un dump SQL."

        if password != get_admin_password():
            return False, "Invalid password."

        if not os.path.exists(backup_path):
            return False, "Backup file not found."
            
        backup_path = str(backup_path) # Ensure string

        try:
            # HYBRID RESTORE STRATEGY
            if self.is_cloud:
                # CLOUD MODE
                if backup_path.lower().endswith(".sql"):
                    # Option A: Restore from SQL Dump (Native)
                    return self._restore_from_sql_dump(backup_path)
                    
                elif backup_path.lower().endswith(".db"):
                    # Option B: Restore from SQLite Backup (Migration)
                    # We treat the backup as a source for migration to Cloud
                    return self._restore_from_sqlite_backup(backup_path)
                
                else:
                    return False, "Formato no soportado en Nube. Use .sql o .db"
            
            else:
                # LOCAL MODE (SQLite)
                if backup_path.lower().endswith(".sql"):
                    return False, "No se puede restaurar un SQL Dump en modo SQLite (Local)."
                
                # Standard File Copy Restore
                # Close existing connections? 
                # In SQLite with file copy, it's risky if the app has the file open.
                # Ideally we should close the session/engine, but for this desktop app
                # a simple copy overwrite might work if no transaction is active.
                
                shutil.copy2(backup_path, self.db_path)
                app_logger.info(f"Database restored from: {backup_path}")
                return True, "Sistema restaurado correctament. Por favor renicie la aplicación."

        except Exception as e:
            app_logger.error(f"Restore failed: {e}")
            return False, str(e)
            
    def export_to_excel_full(self, target_path):
        """Exports all tables to a multi-sheet Excel file (Handles both SQLite and Postgres)."""
        try:
            from sqlalchemy import create_engine, inspect
            
            # Use SQLAlchemy for agnostic connection
            engine = create_engine(self.db_url)
            inspector = inspect(engine)
            
            # Get table names compatible with both
            tables = inspector.get_table_names()
            
            with pd.ExcelWriter(target_path, engine='openpyxl') as writer:
                with engine.connect() as conn:
                    for table in tables:
                        # SKIP BLOB TABLES (Too heavy for Excel)
                        if table == 'documentos': 
                             app_logger.info("Skipping 'documentos' table in Excel backup (BLOBs omitted).")
                             continue

                        df = pd.read_sql_table(table, conn)
                        df.to_excel(writer, sheet_name=table[:31], index=False) # Excel sheet name limit 31 chars
            
            return True, "Export successful."
        except Exception as e:
            app_logger.error(f"Excel export failed: {e}")
            return False, str(e)
            
    def export_to_sql_dump(self, target_path):
        """Exports the database to a SQL dump file."""
        try:
            conn = sqlite3.connect(self.db_path)
            with open(target_path, 'w', encoding='utf-8') as f:
                for line in conn.iterdump():
                    f.write('%s\n' % line)
            conn.close()
            return True, "SQL Dump successful."
        except Exception as e:
            app_logger.error(f"SQL export failed: {e}")
            return False, str(e)
    
    def get_backups_list(self):
        """Returns a list of available backup files."""
        if not self.backup_dir.exists():
            return []
        
        files = [f for f in self.backup_dir.glob("*.db") if f.name.startswith("SIGV_Backup_")]
        return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
        
    def apply_default_rules(self):
        """
        Applies default Adjustment Rules to Obligations that have none.
        - Taxes/Services/Expenses -> ESTACIONAL_IPC
        - Others -> FIJO
        Returns: count of updated records
        """
        db = SessionLocal()
        count = 0
        try:
            # 1. Find Obs without rules
            obs_no_rule = db.query(Obligacion).outerjoin(ReglaAjuste).filter(ReglaAjuste.id == None).all()
            
            for o in obs_no_rule:
                # Determine rule based on category
                cat = o.proveedor.categoria if o.proveedor else None
                new_rule = TipoAjuste.FIJO # Default
                
                if cat in [CategoriaServicio.IMPUESTO, CategoriaServicio.EXPENSA, CategoriaServicio.SERVICIO]:
                    new_rule = TipoAjuste.ESTACIONAL_IPC
                
                # Create Regla
                regla = ReglaAjuste(
                    obligacion_id=o.id,
                    tipo_ajuste=new_rule,
                    frecuencia_meses=1
                )
                db.add(regla)
                count += 1
            
            db.commit()
            return True, f"Se actualizaron {count} obligaciones con reglas por defecto."
            
        except Exception as e:
            db.rollback()
            app_logger.error(f"Error applying default rules: {e}")
            return False, str(e)
        finally:
            db.close()


    def _restore_from_sql_dump(self, sql_path):
        """
        Restores a PostgreSQL database from a SQL Dump file.
        WARNING: This is valid for files generated by generate_cloud_sql_dump.
        """
        try:
            from sqlalchemy import create_engine, text
            
            app_logger.info(f"Starting SQL RESTORE from: {sql_path}")
            
            # 1. Connect
            engine = create_engine(self.db_url)
            
            # 2. Read File
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                
            # 3. Execute
            # Note: We need to split commands carefully or use a specialized runner.
            # Our dumps are simple INSERTs separated by ;
            # But large files might crash if loaded at once?
            # For 2MB it is fine.
            
            with engine.connect() as conn:
                trans = conn.begin()
                try:
                    # A. Truncate Everything (Clean Slate)
                    # Inspector to find tables
                    from sqlalchemy import inspect
                    inspector = inspect(engine)
                    tables = inspector.get_table_names()
                    
                    if tables:
                        tbl_list = ", ".join([f'"{t}"' for t in tables])
                        conn.execute(text(f"TRUNCATE TABLE {tbl_list} RESTART IDENTITY CASCADE"))
                    
                    # B. Execute Script
                    # SQLAlchemy text() with multiple statements works if driver supports it (psycopg2 usually does)
                    # If not, we might need to split by ";\n"
                    
                    # Attempt simple split by semicolon + newline (as generated by us)
                    commands = sql_content.split(";\n")
                    
                    for cmd in commands:
                        if cmd.strip():
                             # Ignore comments
                             if cmd.strip().startswith("--"): continue
                             
                             conn.execute(text(cmd))
                             
                    trans.commit()
                    return True, "Base de datos restaurada desde SQL Dump."
                    
                except Exception as e:
                    trans.rollback()
                    raise e
                    
        except Exception as e:
            app_logger.error(f"SQL Restore failed: {e}")
            return False, f"Error detallado: {e}"

    def _restore_from_sqlite_backup(self, db_path):
        """
        MIGRATION RESTORE:
        Takes an old SQLite backup file, and 'migrates' it to the current Cloud DB.
        """
        try:
            from sqlalchemy import create_engine
            
            # Source: The backup file
            # Handle Windows paths for SQLite URL
            db_path_str = str(db_path).replace(os.sep, "/")
            source_url = f"sqlite:///{db_path_str}"
            source_engine = create_engine(source_url)
            
            # Target: Current Cloud DB
            target_engine = create_engine(self.db_url)
            
            return self._migrate_data(source_engine, target_engine)
            
        except Exception as e:
            app_logger.error(f"SQLite Restore failed: {e}")
            return False, str(e)

    def migrate_sqlite_to_postgres(self, target_url):
        """
        Refactored to use _migrate_data.
        Source is the CURRENT running database (from database.py engine).
        """
        try:
            from sqlalchemy import create_engine
            from database import engine as current_engine
            
            target_engine = create_engine(target_url)
            return self._migrate_data(current_engine, target_engine)
            
        except Exception as e:
            return False, str(e)

    def _migrate_data(self, source_engine, target_engine):
        """
        Core logic to copy data from Source to Target.
        Destroys Target data first!
        """
        try:
            from sqlalchemy import text
            from models.entities import Base
            import pandas as pd
            
            # Ensure Schema exists in Target
            Base.metadata.create_all(target_engine)
            
            tables = [
                "usuarios", 
                "inmuebles", 
                "proveedores", 
                "obligaciones", 
                "reglas_ajuste", 
                "vencimientos", 
                "pagos", 
                "indices_economicos", 
                "cotizaciones", 
                "periodos_contables", 
                "credenciales",
                "audit_logs"
            ]
            
            with source_engine.connect() as src_conn:
                with target_engine.connect() as tgt_conn:
                    trans = tgt_conn.begin()
                    try:
                        # CLEAN TARGET
                        tgt_tables_sql = ", ".join([f'"{t}"' for t in tables])
                        try:
                            tgt_conn.execute(text(f"TRUNCATE TABLE {tgt_tables_sql} RESTART IDENTITY CASCADE"))
                        except Exception:
                            pass # Tables might not exist

                        for table in tables:
                            # Read Source
                            try:
                                df = pd.read_sql_table(table, src_conn)
                            except ValueError: 
                                # Table might not exist in source (e.g. older backup)
                                continue
                                
                            if not df.empty:
                                # Write Target
                                df.to_sql(table, tgt_conn, if_exists='append', index=False)
                                
                                # Reset Sequence (Postgres)
                                if 'id' in df.columns:
                                    try:
                                        seq_sql = text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), coalesce(max(id), 1)) FROM {table}")
                                        tgt_conn.execute(seq_sql)
                                    except Exception:
                                        pass
                                    
                        trans.commit()
                        app_logger.info("Migration/Restore completed successfully.")
                        return True, "Operación completada exitosamente."
                        
                    except Exception as e:
                        trans.rollback()
                        raise e
                        
        except Exception as e:
            app_logger.error(f"Data Transfer failed: {e}")
            return False, f"Error de Transferencia: {e}"

    def generate_cloud_sql_dump(self, target_path, progress_callback=None):
        """
        Generates a complete SQL Dump (INSERTS) for Postgres.
        Handles BLOBs using Hex encoding (\\x...).
        Stream-writes to file to minimize RAM usage.
        progress_callback: function(percent, message)
        """
        try:
            from sqlalchemy import create_engine, inspect, text
            import binascii
            import os
            from datetime import date, datetime
            
            engine = create_engine(self.db_url)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            ordered_tables = [
                "config_years", "usuarios", "inmuebles", "proveedores", "indices_economicos",
                "cotizaciones", "periodos_contables", "documentos", # Docs indep
                "obligaciones", "reglas_ajuste", 
                "vencimientos", "pagos", "credenciales", "audit_logs"
            ]
            for t in tables: 
                if t not in ordered_tables and t != "alembic_version":
                    ordered_tables.append(t)

            # 1. Count Totals for Progress
            total_rows = 0
            if progress_callback:
                progress_callback(0, "Calculando registros...")
                try:
                    with engine.connect() as conn:
                        for t in ordered_tables:
                            if t in tables:
                                # Fast count
                                r = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                                total_rows += r
                except:
                    total_rows = 1000 # Fallback
                
            current_count = 0

            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(f"-- SIGV Cloud Backup (Postgres Dump)\n")
                f.write(f"-- Generated: {datetime.now()}\n\n")
                f.write("SET session_replication_role = 'replica';\n\n")
                
                with engine.connect() as conn:
                    for table in ordered_tables:
                        if table not in tables: continue
                        
                        if progress_callback:
                            progress_callback(0, f"Exportando {table}...") # Percent managed by row count
                        
                        f.write(f"-- Data for {table}\n")
                        
                        cols = [c['name'] for c in inspector.get_columns(table)]
                        cols_str = ", ".join(cols)
                        
                        result = conn.execute(text(f"SELECT * FROM {table}")) # Stream
                        
                        table_count = 0
                        for row in result:
                            # Update Progress
                            current_count += 1
                            if progress_callback and total_rows > 0 and current_count % 10 == 0:
                                pct = (current_count / total_rows)
                                progress_callback(pct, f"Exportando {table} ({table_count})")

                            vals = []
                            for val in row:
                                if val is None:
                                    vals.append("NULL")
                                elif isinstance(val, (bytes, bytearray, memoryview)):
                                    if isinstance(val, memoryview):
                                        val = val.tobytes()
                                    hex_str = binascii.hexlify(val).decode('utf-8')
                                    vals.append(f"'\\x{hex_str}'")
                                elif isinstance(val, (date, datetime)):
                                    vals.append(f"'{val.isoformat()}'")
                                elif isinstance(val, str):
                                    safe_str = val.replace("'", "''")
                                    vals.append(f"'{safe_str}'")
                                else:
                                    vals.append(str(val))
                            
                            vals_str = ", ".join(vals)
                            f.write(f"INSERT INTO {table} ({cols_str}) VALUES ({vals_str});\n")
                            table_count += 1
                        
                        f.write(f"\n-- {table_count} rows exported for {table}\n\n")

                f.write("SET session_replication_role = 'origin';\n")
            
            return True, f"Backup SQL Completo generado exitosamente.\nGuardado en: {os.path.basename(target_path)}"

        except Exception as e:
            app_logger.error(f"SQL Cloud Export failed: {e}")
            return False, str(e)

    def create_source_zip(self, target_path, progress_callback=None):
        """
        Zips the entire application source code (excluding venv/git).
        Useful for backing up the 'software' state.
        """
        import zipfile
        
        excluded_dirs = {'.venv', 'venv', '__pycache__', '.git', '.idea', '.vscode', 'backups', 'dist', 'build'}
        excluded_files = {'*.pyc', '*.log', '*.db', '*.sqlite'} # Exclude active DBs to avoid lock errors
        
        try:
            root_dir = os.getcwd()
            total_files = 0
            
            # 1. Count
            if progress_callback:
                progress_callback(0, "Escaneando archivos...")
                for root, dirs, files in os.walk(root_dir):
                    # Filter dirs in-place
                    dirs[:] = [d for d in dirs if d not in excluded_dirs]
                    total_files += len(files)
            
            # 2. Zip
            count_processed = 0
            with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(root_dir):
                    dirs[:] = [d for d in dirs if d not in excluded_dirs]
                    
                    for file in files:
                        if file.endswith(".pyc") or file.endswith(".log"): continue
                        
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, root_dir)
                        
                        zf.write(file_path, rel_path)
                        
                        count_processed += 1
                        if progress_callback and total_files > 0 and count_processed % 10 == 0:
                            pct = count_processed / total_files
                            progress_callback(pct, f"Comprimiendo {file}...")
                            
            return True, f"Código Fuente empaquetado exitosamente.\n{os.path.basename(target_path)}"
            
        except Exception as e:
            app_logger.error(f"Zip Backup failed: {e}")
            return False, str(e)


