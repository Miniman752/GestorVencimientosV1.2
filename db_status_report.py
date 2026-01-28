import os
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def print_db_status():
    print(f"--- ESTADO DE BASE DE DATOS NEON.TECH ---")
    print(f"URL: {DATABASE_URL.split('@')[1]}") # Hide credentials, show host
    
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        tables = ['vencimientos', 'proveedores', 'inmuebles', 'obligaciones', 'usuarios']
        
        print(f"\n{'TABLA':<20} | {'REGISTROS':<10}")
        print("-" * 35)
        
        total_records = 0
        for table in tables:
            try:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"{table.capitalize():<20} | {count:<10}")
                total_records += count
            except Exception as e:
                print(f"{table.capitalize():<20} | Error: {e}")
        
        print("-" * 35)
        print(f"Total Registros (aprox): {total_records}")

if __name__ == "__main__":
    import sys
    with open("neon_status.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        print_db_status()
        sys.stdout = sys.__stdout__
    
    with open("neon_status.txt", "r", encoding="utf-8") as f:
        print(f.read())
