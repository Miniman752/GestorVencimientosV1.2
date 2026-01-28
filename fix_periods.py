
from database import SessionLocal
from models.entities import Vencimiento
from sqlalchemy import text

def fix_periods():
    session = SessionLocal()
    try:
        print("Checking for malformed periods (MM-YYYY)...")
        # Find records where period matches pattern like '12-2025' (starts with 2 digits then dash)
        # Note: '2025-12' starts with 4 digits.
        # SQLite globs or just python filtering since specific logic?
        # User is on Postgres per config.ini?
        # Let's filter in python to be safe and database agnostic for this fix.
        
        all_venc = session.query(Vencimiento).all()
        count = 0
        for v in all_venc:
            if v.periodo and '-' in v.periodo:
                parts = v.periodo.split('-')
                # If first part is 2 digits and second is 4 digits -> Swap
                if len(parts[0]) == 2 and len(parts[1]) == 4:
                    old = v.periodo
                    new_p = f"{parts[1]}-{parts[0]}"
                    v.periodo = new_p
                    print(f"Fixed ID {v.id}: {old} -> {new_p}")
                    count += 1
        
        if count > 0:
            session.commit()
            print(f"Successfully fixed {count} records.")
        else:
            print("No malformed periods found.")
            
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    fix_periods()
