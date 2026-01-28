from services.period_service import PeriodService
from database import SessionLocal
from datetime import date
from models.entities import EstadoPeriodo

target = date(2026, 1, 1)

print(f"Checking status for {target} (Period ID: {PeriodService.get_period_id(target)})")

try:
    with SessionLocal() as session:
        # 1. Check raw DB
        from models.entities import PeriodoContable
        p = session.query(PeriodoContable).filter_by(periodo_id="2026-01").first()
        if p:
            print(f"DB Record Found: {p.periodo_id}, Status: {p.estado} (Type: {type(p.estado)})")
        else:
            print("DB Record NOT found for 2026-01")
            
        # 2. Check Service
        status = PeriodService.check_period_status(target, session=session)
        print(f"Service returned: {status} (Type: {type(status)})")
        
        expected = EstadoPeriodo.ABIERTO
        print(f"Does it equal Expected ABIERTO? {status == expected}")
        
        if status == EstadoPeriodo.CERRADO:
            print("Result: CLOSED")
        else:
            print("Result: OPEN (or other)")

except Exception as e:
    print(f"CAUGHT EXCEPTION: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
