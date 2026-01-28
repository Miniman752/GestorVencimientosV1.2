from sqlalchemy import create_engine, inspect
from config import DATABASE_URL

def check_constraints():
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    tables = ['indices_economicos', 'pagos', 'vencimientos']
    
    with open("constraints_report.txt", "w", encoding="utf-8") as f:
        for t in tables:
            f.write(f"\n--- Table: {t} ---\n")
            for c in inspector.get_columns(t):
                # c is dict: name, type, nullable, default, ...
                if not c['nullable'] and c['default'] is None and not c.get('autoincrement', False) and c['name'] != 'id':
                     f.write(f"  CRITICAL: {c['name']} is NOT NULL and has NO DEFAULT in DB.\n")

if __name__ == "__main__":
    check_constraints()
