
import sqlalchemy
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://neondb_owner:npg_vhmWRL8ESXI3@ep-green-night-acbu7krn-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

def check_enum():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        try:
            result = conn.execute(text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'rolusuario'"))
            print(f"Valid 'rolusuario' values: {[row[0] for row in result]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_enum()
