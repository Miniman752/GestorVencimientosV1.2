import os
import sys
import subprocess
import datetime
import configparser
from pathlib import Path

# Fix for Windows Console Encoding (Emojis)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 doesn't support reconfigure, but we are on 3.13 likely
        pass

# --- Configuration ---
BACKUP_DIR = Path("backups")
CONFIG_FILE = Path("config.ini")

def get_database_url():
    """Reads the active DB URL from config.ini."""
    if not CONFIG_FILE.exists():
        print("Error: config.ini not found.")
        return None
        
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    if "General" in config and "last_db" in config["General"]:
        return config["General"]["last_db"]
    return None

def find_pg_dump():
    """Attempts to find pg_dump.exe in common PostgreSQL paths."""
    # List of common paths
    common_paths = [
        r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\13\bin\pg_dump.exe",
        r"C:\Program Files (x86)\PostgreSQL\16\bin\pg_dump.exe",
    ]
    
    # Check PATH first
    import shutil
    if shutil.which("pg_dump"):
        return "pg_dump"
        
    # Check common folders
    for path in common_paths:
        if os.path.exists(path):
            return path
            
    return None

def main():
    print("--- 🛡️ GESTOR DE VENCIMIENTOS: CLOUD BACKUP ---")
    
    # 1. Setup Backup Dir
    if not BACKUP_DIR.exists():
        BACKUP_DIR.mkdir()
        
    # 2. Get URL
    db_url = get_database_url()
    if not db_url or "postgresql" not in db_url:
        print("❌ Error: No Cloud Database URL found in config.ini")
        input("Press Enter to exit...")
        return
        
    print(f"Target Database: Neon (Cloud)")
    
    # 3. Find Tool
    pg_dump_bin = find_pg_dump()
    if not pg_dump_bin:
        print("❌ Error: Could not find 'pg_dump.exe' locally.")
        print("Please ensure PostgreSQL is installed or add it to system PATH.")
        input("Press Enter to exit...")
        return
    print(f"Using Backup Tool: {pg_dump_bin}")

    # 4. Generate Filename
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"Backup_Cloud_{timestamp}.sql"
    filepath = BACKUP_DIR / filename
    
    # 5. Execute Backup
    print("⏳ Downloading data from Cloud... (This may take a moment)")
    
    # Build Command
    # pg_dump -d "url" -f "file"
    cmd = [pg_dump_bin, str(db_url), "-f", str(filepath), "--no-owner", "--no-acl", "--clean", "--if-exists"]
    
    try:
        # Hide password in environment, not args if possible, but passing URL handles it mostly.
        # However, passing URL directly to pg_dump works well.
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ SUCCESS! Backup saved to:\n   {filepath.absolute()}")
            print(f"   Size: {os.path.getsize(filepath) / 1024:.2f} KB")
        else:
             print("❌ BACKUP FAILED!")
             print("Error Output:")
             print(result.stderr)
             

    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

    # 6. Replication to Cloud/OneDrive
    if "--skip-replication" in sys.argv:
        print("⏩ Skipping Cloud Replication (--skip-replication flag detected).")
    else:
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        if "General" in config and "cloud_backup_path" in config["General"]:
            custom_path = Path(config["General"]["cloud_backup_path"])
            if custom_path.exists():
                print(f"☁️ Replicating to User Cloud: {custom_path}")
                try:
                    import shutil
                    shutil.copy2(filepath, custom_path / filename)
                    print("   -> Success! Copy saved to OneDrive/Cloud.")
                except Exception as e:
                    print(f"   -> Warning: Could not copy to cloud path: {e}")

    # Only pause if not running in automated mode (simple check)
    if not "--no-pause" in sys.argv:
        input("\nPress Enter to close...")

if __name__ == "__main__":
    main()
