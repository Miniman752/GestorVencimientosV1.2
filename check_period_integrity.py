import sys
import os
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def check_periods():
    print("Checking Period Formats in DB...")
    
    # 01-2026 pattern: Starts with 2 digits, dash, 4 digits. Or just check for YYYY-MM
    # Correct: ^\d{4}-\d{2}$
    # Incorrect: ^\d{2}-\d{4}$ (e.g. 01-2024)
    # We can use Regex in Postgres: '^\d{2}-\d{4}'
    
    query = text("""
        SELECT id, periodo, fecha_vencimiento 
        FROM vencimientos 
        WHERE periodo ~ '^\\d{2}-\\d{4}'
    """)
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            results = conn.execute(query).fetchall()
            
            if results:
                print(f"❌ Found {len(results)} records with INVALID format (MM-YYYY):")
                for r in results[:5]:
                    print(f"   ID: {r.id} | Period: {r.periodo} | Date: {r.fecha_vencimiento}")
                if len(results) > 5: print("   ... and more.")
                
                # Verify logic: The period should match YYYY-MM of the date
                print("\nVerification: these likely need swapping.")
            else:
                print("✅ No records found with MM-YYYY format.")
                
            # Secondary Check: Disconnects
            # Period != Date.strftime('%Y-%m')
            
            # Note: Postgres to_char(date, 'YYYY-MM')
            query_mismatch = text("""
                SELECT id, periodo, fecha_vencimiento
                FROM vencimientos
                WHERE periodo != to_char(fecha_vencimiento, 'YYYY-MM')
                AND is_deleted = 0
            """)
            
            mismatches = conn.execute(query_mismatch).fetchall()
            if mismatches:
                 print(f"⚠️ Found {len(mismatches)} records where Period doesn't match Date (YYYY-MM):")
                 for r in mismatches[:5]:
                     print(f"   ID {r.id}: P='{r.periodo}' vs D='{r.fecha_vencimiento}'")
            else:
                 print("✅ All active records match Date derived period.")

    except Exception as e:
        print(f"Error checking DB: {e}")

if __name__ == "__main__":
    check_periods()
