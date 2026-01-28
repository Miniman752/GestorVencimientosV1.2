
import sys
import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import DATABASE_URL
from models.entities import Base, Inmueble, ProveedorServicio, Obligacion, Vencimiento, Pago, Usuario, Credencial, IndiceEconomico, Cotizacion, PeriodoContable, AuditLog, ReglaAjuste

# TARGET BACKUP (Found to have 22 records)
BACKUP_PATH = r"backups\SIGV_Backup_2026-01-12_1625.db"

print("--- RESTORING FROM BACKUP TO CLOUD ---")
print(f"Source: {BACKUP_PATH}")
print(f"Target: Neon.tech Cloud")

if not os.path.exists(BACKUP_PATH):
    print("ERROR: Backup file not found!")
    sys.exit(1)

# 1. Source Connection
source_engine = create_engine(f"sqlite:///{BACKUP_PATH}")

# 2. Target Connection
target_engine = create_engine(DATABASE_URL)

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

try:
    with source_engine.connect() as src_conn:
        with target_engine.connect() as tgt_conn:
            trans = tgt_conn.begin()
            try:
                # OPTIONAL: Truncate target to avoid duplicates/conflicts?
                # Since cloud has only 1 test record, better clear it to be clean.
                print("Cleaning cloud database...")
                tgt_tables_sql = ", ".join([f'"{t}"' for t in tables])
                tgt_conn.execute(text(f"TRUNCATE TABLE {tgt_tables_sql} RESTART IDENTITY CASCADE"))
                
                for table in tables:
                    print(f"Migrating table: {table}...")
                    try:
                        df = pd.read_sql_table(table, src_conn)
                        if not df.empty:
                            df.to_sql(table, tgt_conn, if_exists='append', index=False)
                            print(f"  -> {len(df)} records copied.")
                            
                            # Reset Sequence
                            if 'id' in df.columns:
                                try:
                                    seq_sql = text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), coalesce(max(id), 1)) FROM {table}")
                                    tgt_conn.execute(seq_sql)
                                except: pass
                    except ValueError:
                        print(f"  -> Table {table} not in source (skipping).")
                        
                trans.commit()
                print("\nSUCCESS: Cloud database restored from backup!")
                
            except Exception as e:
                trans.rollback()
                print(f"ERROR During Transaction: {e}")
                
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
