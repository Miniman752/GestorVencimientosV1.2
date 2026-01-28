import sys
import os
import traceback

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_imports():
    print("--- CHECKING IMPORTS ---")
    try:
        import models.entities
        print("✅ models.entities imported")
        import controllers.forex_controller
        print("✅ controllers.forex_controller imported")
        import views.forex_view
        print("✅ views.forex_view imported")
        import services.bna_service
        print("✅ services.bna_service imported")
        return True
    except Exception as e:
        print(f"❌ Import Failed: {e}")
        traceback.print_exc()
        return False

def check_db_connection():
    print("\n--- CHECKING DB CONNECTION ---")
    try:
        from database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        print("✅ Database Connected")
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database Connection Failed: {e}")
        traceback.print_exc()
        return False

def check_year_config_model():
    print("\n--- CHECKING YEAR CONFIG MODEL ---")
    try:
        from models.entities import YearConfig
        from sqlalchemy.inspection import inspect
        print(f"YearConfig.is_active type: {YearConfig.is_active.type}")
        return True
    except Exception as e:
        print(f"❌ Model Check Failed: {e}")
        traceback.print_exc()
        return False

def main():
    if check_imports() and check_db_connection() and check_year_config_model():
        print("\n✅ SYSTEM HEALTH CHECK PASSED")
    else:
        print("\n❌ SYSTEM HEALTH CHECK FAILED")

if __name__ == "__main__":
    main()
