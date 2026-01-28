import os
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def inspect_dupes():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Inspecting Vencimientos 29 and 33:")
        query = text("SELECT * FROM vencimientos WHERE id IN (29, 33)")
        rows = conn.execute(query).fetchall()
        
        # Get column names
        keys = rows[0]._mapping.keys()
        
        results = []
        for r in rows:
            d = dict(zip(keys, r))
            results.append(d)
            
        import json
        # Handle date serialization
        def default(o):
            if hasattr(o, 'isoformat'):
                return o.isoformat()
            return str(o)
            
        print(json.dumps(results, default=default, indent=2))

if __name__ == "__main__":
    import sys
    with open("dupe_details.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        inspect_dupes()
        sys.stdout = sys.__stdout__
    
    with open("dupe_details.txt", "r", encoding="utf-8") as f:
        print(f.read())
