from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
from models.entities import Vencimiento

def check_2026():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        count = session.query(Vencimiento).filter(Vencimiento.periodo.endswith('2026')).count()
        print(f"Total records for 2026: {count}")
        
        if count > 0:
            # Show breakdown by month
            print("\nBreakdown by Period:")
            from sqlalchemy import func
            breakdown = session.query(Vencimiento.periodo, func.count(Vencimiento.id)).filter(Vencimiento.periodo.endswith('2026')).group_by(Vencimiento.periodo).all()
            for p, c in breakdown:
                print(f"  {p}: {c} records")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_2026()
