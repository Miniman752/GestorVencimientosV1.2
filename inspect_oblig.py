
from sqlalchemy import create_engine, inspect
from config import DATABASE_URL
import sys

def inspect_obligaciones():
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        print("====== COLUMNS FOR OBLIGACIONES ======")
        for col in inspector.get_columns('obligaciones'):
            print(f"- {col['name']} ({col['type']})")
        print("======================================")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_obligaciones()
