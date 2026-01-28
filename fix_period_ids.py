from database import SessionLocal
from models.entities import Vencimiento, PeriodoContable
from sqlalchemy import text

def migrate():
    session = SessionLocal()
    try:
        # 1. Fix Vencimientos
        print("Migrating Vencimientos...")
        vencs = session.query(Vencimiento).all()
        count = 0
        for v in vencs:
            if v.periodo and len(v.periodo) == 7:
                # Check format MM-YYYY (e.g. 12-2025)
                # Heuristic: If first part <= 12 and second part > 1900
                parts = v.periodo.split('-')
                if len(parts) == 2:
                    p1, p2 = parts[0], parts[1]
                    if len(p1) == 2 and len(p2) == 4:
                        if int(p1) <= 12 and int(p2) > 2000:
                            # It is MM-YYYY. Flip to YYYY-MM
                            new_p = f"{p2}-{p1}"
                            v.periodo = new_p
                            count += 1
        
        session.commit()
        print(f"Updated {count} Vencimientos to YYYY-MM.")

        # 2. Check Periodos Contables for MM-YYYY and fix them
        print("Checking Periodos...")
        periods = session.query(PeriodoContable).all()
        p_count = 0
        for p in periods:
             if p.periodo_id and len(p.periodo_id) == 7:
                 parts = p.periodo_id.split('-')
                 if len(parts) == 2:
                     p1, p2 = parts[0], parts[1]
                     # If MM-YYYY (12-2025)
                     if len(p1) == 2 and len(p2) == 4:
                         if int(p1) <= 12 and int(p2) > 2000:
                             correct_id = f"{p2}-{p1}"
                             print(f"Fixing Periodo: {p.periodo_id} -> {correct_id}")
                             
                             # Check if target exists
                             existing = session.query(PeriodoContable).get(correct_id)
                             if not existing:
                                 # Clone and recreate
                                 # Warning: SQLAlchemy might track this object.
                                 # Use raw SQL or detatch for safety?
                                 # Creating new object is fine.
                                 new_p = PeriodoContable(
                                     periodo_id=correct_id,
                                     estado=p.estado,
                                     fecha_cierre=p.fecha_cierre,
                                     notas=p.notas
                                 )
                                 session.add(new_p)
                             
                             # Delete old (orphans are okay as Vencimientos allow string FK or we updated them already)
                             session.delete(p)
                             p_count += 1
        session.commit()
        print(f"Updated {p_count} Periodos.")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
