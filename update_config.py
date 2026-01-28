
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import save_last_db_path

NEW_URL = "postgresql://neondb_owner:npg_vhmWRL8ESXI3@ep-green-night-acbu7krn-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

print(f"Updating configuration to: {NEW_URL}")
save_last_db_path(NEW_URL)
print("Configuration updated.")
