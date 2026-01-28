import os
import sys
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def inspect_enum():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            with open("db_schema.txt", "w", encoding="utf-8") as f:
                f.write("--- Inspecting Enum 'tipoajuste' ---\n")
                query = text("""
                    SELECT e.enumlabel
                    FROM pg_enum e
                    JOIN pg_type t ON e.enumtypid = t.oid
                    WHERE t.typname = 'tipoajuste';
                """)
                result = conn.execute(query)
                labels = [row[0] for row in result]
                f.write(f"Allowed values for 'tipoajuste': {labels}\n")
                
                f.write("\n--- Inspecting Table 'reglas_ajuste' ---\n")
                q2 = text("""
                    SELECT column_name, data_type, udt_name
                    FROM information_schema.columns
                    WHERE table_name = 'reglas_ajuste';
                """)
                res2 = conn.execute(q2)
                for row in res2:
                    f.write(f"{row}\n")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_enum()
