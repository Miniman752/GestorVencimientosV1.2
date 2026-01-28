
from sqlalchemy import create_engine, inspect
from config import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)

def inspect_db():
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        print(f"Connected to: {DATABASE_URL.split('@')[1]}") # Hide credentials
        
        tables = ['usuarios', 'obligaciones', 'proveedores']
        
        for table in tables:
            print(f"\n--- TABLE: {table} ---")
            if inspector.has_table(table):
                columns = inspector.get_columns(table)
                for col in columns:
                    print(f"  - {col['name']} ({col['type']})")
            else:
                print("  [TABLE NOT FOUND]")
                
    except Exception as e:
        print(f"Error inspecting DB: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    inspect_db()
    sys.stdout.flush()
