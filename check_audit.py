from sqlalchemy import create_engine, inspect
from config import DATABASE_URL

def inspect_audit():
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    cols = inspector.get_columns('audit_logs')
    print("Columns in audit_logs:")
    for c in cols:
        print(f" - {c['name']} ({c['type']})")

inspect_audit()
