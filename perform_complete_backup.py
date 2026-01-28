import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from controllers.db_admin_controller import DbAdminController
from config import get_backup_dir

def perform_backup():
    controller = DbAdminController()
    backup_dir = get_backup_dir()
    
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True)
        
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    
    print(f"--- STARTING FULL BACKUP {ts} ---")
    print(f"Directory: {backup_dir}")
    
    # 1. SQL Dump
    print("\n[1/2] Generating Cloud SQL Dump...")
    sql_file = backup_dir / f"FULL_DB_DUMP_{ts}.sql"
    success_sql, msg_sql = controller.generate_cloud_sql_dump(str(sql_file))
    
    if success_sql:
        print(f"✅ SQL Dump OK: {sql_file.name}")
    else:
        print(f"❌ SQL Dump FAILED: {msg_sql}")
        
    # 2. Source Code Zip
    print("\n[2/2] Archiving Source Code...")
    zip_file = backup_dir / f"FULL_APP_SOURCE_{ts}.zip"
    success_zip, msg_zip = controller.create_source_zip(str(zip_file))
    
    if success_zip:
        print(f"✅ Source Zip OK: {zip_file.name}")
    else:
        print(f"❌ Source Zip FAILED: {msg_zip}")
        
    print("\n--- BACKUP COMPLETE ---")
    if success_sql and success_zip:
        print("All systems backed up successfully.")
    else:
        print("Some backups failed. Check output.")

if __name__ == "__main__":
    perform_backup()
