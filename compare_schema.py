import sys
from sqlalchemy import create_engine, inspect, Text, String, Enum
from config import DATABASE_URL
from models.entities import Base

def compare_schema():
    print("Initiating schema check...")
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    db_tables = set(inspector.get_table_names())
    model_tables = set(Base.metadata.tables.keys())

    with open("schema_report_utf8.txt", "w", encoding="utf-8") as f:
        f.write(f"Connecting to: {DATABASE_URL}\n")
        
        f.write(f"\n--- TABLES CHECK ---\n")
        missing_in_db = model_tables - db_tables
        extra_in_db = db_tables - model_tables
        
        if missing_in_db:
            f.write(f"❌ MISSING IN DB (Defined in Code but not in Postgres): {missing_in_db}\n")
        if extra_in_db:
            f.write(f"⚠️  EXTRA IN DB (In Postgres but not in Code): {extra_in_db}\n")
            
        f.write(f"\n--- COLUMNS CHECK ---\n")
        
        issues_found = False
        
        for table_name in model_tables:
            if table_name not in db_tables:
                continue
                
            f.write(f"Checking table '{table_name}'...\n")
            
            # Get DB columns
            db_cols = inspector.get_columns(table_name)
            db_col_map = {c['name']: c for c in db_cols}
            
            # Get Model columns
            model_table = Base.metadata.tables[table_name]
            
            for model_col in model_table.columns:
                cname = model_col.name
                
                if cname not in db_col_map:
                    f.write(f"  ❌ MISSING COLUMN in DB: {table_name}.{cname}\n")
                    issues_found = True
                    continue
                    
                # Type check (Loose)
                db_col_def = db_col_map[cname]
                
                # Check for Enum mismatch heuristic
                is_model_enum = isinstance(model_col.type, (Enum,)) or "Enum" in str(model_col.type)
                is_db_enum = "USER-DEFINED" in str(db_col_def['type']) or "enum" in str(db_col_def['type']).lower()
                
                if is_model_enum and not is_db_enum:
                     # Check if DB is at least String
                     if "VARCHAR" not in str(db_col_def['type']).upper() and "TEXT" not in str(db_col_def['type']).upper():
                         f.write(f"  ⚠️  TYPE MISMATCH: {table_name}.{cname} (Model: Enum, DB: {db_col_def['type']})\n")

        if not issues_found:
            f.write("\n✅ All Model columns exist in DB.\n")
        else:
            f.write("\n❌ Discrepancies found.\n")

if __name__ == "__main__":
    try:
        compare_schema()
        print("Done. Report saved to schema_report_utf8.txt")
    except Exception as e:
        print(f"Error: {e}")
