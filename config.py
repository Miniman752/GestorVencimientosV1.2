import os
import sys
import configparser
from pathlib import Path

# Directorio base del proyecto
# Compatibilidad con PyInstaller (Frozen)
# Compatibilidad con PyInstaller (Frozen)
if getattr(sys, 'frozen', False):
    EXE_DIR = Path(sys.executable).parent
    MEIPASS_DIR = Path(getattr(sys, '_MEIPASS', EXE_DIR))
    
    BASE_DIR = EXE_DIR  # Data, Logs, Backups stay with the EXE
    
    # Check for config in EXE folder first (User Override), then Internal (Bundled)
    if (EXE_DIR / "config.ini").exists():
        CONFIG_FILE = EXE_DIR / "config.ini"
    elif (MEIPASS_DIR / "config.ini").exists():
        CONFIG_FILE = MEIPASS_DIR / "config.ini"
    else:
        CONFIG_FILE = EXE_DIR / "config.ini" # Default creation target
else:
    BASE_DIR = Path(__file__).resolve().parent
    CONFIG_FILE = BASE_DIR / "config.ini"

# Configuración de Rutas de Archivos
APP_DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "Documentacion_Sistema"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"

for d in [APP_DATA_DIR, DOCS_DIR, LOGS_DIR, BACKUPS_DIR]:
    if not d.exists():
        d.mkdir(parents=True)

# --- Configuration Persistence ---
def load_last_db_path():
    """Reads the last opened DB from config.ini. Returns default if not found."""
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
        if "General" in config and "last_db" in config["General"]:
            path = config["General"]["last_db"]
            # Allow PostgreSQL URLs or Existing Files
            if path and path.lower() != "none":
                if path.startswith("postgresql") or os.path.exists(path):
                    return path
    
    # Default fallback
    # Default fallback - FORCE POSTGRES for this user environment
    print(f"DEBUG: Config fallback. Forcing Postgres.")
    return "postgresql://neondb_owner:npg_vhmWRL8ESXI3@ep-green-night-acbu7krn-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"
    # return str(BASE_DIR / "vencimientos.db")

def save_last_db_path(path):
    """Saves the given path to config.ini"""
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
    
    if "General" not in config:
        config["General"] = {}
    
    config["General"]["last_db"] = str(path)
    
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

def get_backup_dir():
    """Reads custom backup dir from config or returns default."""
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
        if "General" in config and "backup_dir" in config["General"]:
            path = config["General"]["backup_dir"]
            if os.path.exists(path):
                return Path(path)
    return BACKUPS_DIR

def set_backup_dir(path):
    """Saves custom backup dir to config.ini"""
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
    
    if "General" not in config:
        config["General"] = {}
    
    config["General"]["backup_dir"] = str(path)
    
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

def get_cloud_backup_path():
    """Returns the configured custom cloud path or None."""
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
        if "General" in config and "cloud_backup_path" in config["General"]:
            path = config["General"]["cloud_backup_path"]
            if os.path.exists(path):
                return Path(path)
    return None

def set_cloud_backup_path(path):
    """Saves the cloud backup preference."""
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
    
    if "General" not in config:
        config["General"] = {}
    
    config["General"]["cloud_backup_path"] = str(path)
    
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

def get_cloud_checked_flag():
    """Returns True if we have already nagged the user about cloud."""
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
        if "General" in config:
            return config["General"].getboolean("cloud_setup_checked", False)
    return False

def set_cloud_checked_flag(value=True):
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
    
    if "General" not in config: config["General"] = {}
    
    config["General"]["cloud_setup_checked"] = str(value)
    
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

# --- Dynamic DB Config ---
DB_PATH_STR = load_last_db_path()

# For Cloud Deploy (Railway/Render) we check env var FIRST
ENV_DB_URL = os.environ.get("DATABASE_URL")

if ENV_DB_URL:
    # Cleanup common copy-paste errors (extra psql prefix or quotes)
    clean_url = ENV_DB_URL.strip().replace("psql ", "").strip("'").strip('"')
    DATABASE_URL = clean_url
    DB_NAME = "Cloud Database"
elif DB_PATH_STR and DB_PATH_STR.startswith("postgresql"):
    # It is a full connection string
    DATABASE_URL = DB_PATH_STR
    DB_NAME = "PostgreSQL Server" # Generic name for display
else:
    # It is a generic file path (SQLite)
    DATABASE_URL = f"sqlite:///{DB_PATH_STR.replace(os.sep, '/')}"
    DB_NAME = os.path.basename(DB_PATH_STR)


# Configuración de la UI
APP_TITLE = "SIGV-Pro: Gestor de Vencimientos"
APP_GEOMETRY = "1200x800"
THEME_COLOR = "blue"  # CustomTkinter theme

# Corporate Real Estate Professional Theme
COLORS = {
    "sidebar_background": "#2C3E50",  # Midnight Blue
    "main_background": "#F4F6F7",     # Cloud White
    "content_surface": "#FFFFFF",     # Pure White
    "primary_button": "#2980B9",      # Belize Blue
    "primary_button_hover": "#3498DB",
    "secondary_button": "#95A5A6",    # Concrete Grey
    "text_primary": "#2C3E50",        # Midnight Blue text (High contrast)
    "text_light": "#ECF0F1",          # Light text for dark backgrounds
    # Semantic
    "status_paid": "#27AE60",         # Nephritis Green
    "status_pending": "#F39C12",      # Brick Orange
    "status_overdue": "#C0392B",      # Pomegranate Red
    "accent_purple": "#7D3C98",       # Wisteria Purple (AI/Cloud)
    "card_background": "#FFFFFF",     # Default Card (Same as surface)
}

# --- UI Constants ---
FILTER_ALL_OPTION = "Todos"

# --- Security Configuration ---
def get_admin_password():
    """
    Returns the admin password from config.ini or default.
    Allows user to change it without code edits.
    """
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
        if "Security" in config and "admin_password" in config["Security"]:
            return config["Security"]["admin_password"]
    return "admin123" # Default fallback

FONTS = {
    "main": "Segoe UI",
    "heading": ("Segoe UI", 20, "bold"),
    "body": ("Segoe UI", 12),
    "small": ("Segoe UI", 10),
}