
import sys
import os
from sqlalchemy import create_engine, text

# Add src to path
sys.path.append(os.getcwd())
from config import DATABASE_URL as DB_URL

def inspect_enums():
    print(f"Connecting to: {DB_URL}")
    engine = create_engine(DB_URL)
    conn = engine.connect()
    
    try:
        print("\n--- Enum Values for 'categoriaservicio' ---")
        # Note: Type name usually lowercased by SQLAlchemy if created that way.
        try:
            result = conn.execute(text("SELECT unnest(enum_range(NULL::categoriaservicio))")).fetchall()
            for r in result:
                print(r[0])
        except Exception as e:
            print(f"Error querying enum: {e}")
            # Try quoted if case sensitive?
            # Or try querying pg_type directly
            print("Querying pg_type...")
            q = text("""
                SELECT e.enumlabel
                FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'categoriaservicio'
            """)
            result = conn.execute(q).fetchall()
            for r in result:
                print(r[0])

    except Exception as e:
        print(f"General Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_enums()
