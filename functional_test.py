import sys
import os
import traceback
from datetime import date

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_tests():
    print("🚀 STARTING FUNCTIONAL SYSTEM VERIFICATION")
    
    # 1. Database & Models
    try:
        from database import SessionLocal
        from models.entities import Cotizacion, Moneda, EstadoPeriodo
        db = SessionLocal()
        print("✅ DB Connection: OK")
        
        # Verify Cotizacion Model
        try:
            c = Cotizacion(compra=1.0, venta=2.0)
            print("✅ Cotizacion Model (compra/venta): OK")
        except Exception as e:
            print(f"❌ Cotizacion Model Error: {e}")

        # Verify EstadoPeriodo
        try:
            if EstadoPeriodo.BLOQUEADO:
                print("✅ EstadoPeriodo.BLOQUEADO: OK")
        except AttributeError:
            print("❌ EstadoPeriodo.BLOQUEADO missing")

        db.close()
    except Exception as e:
        print(f"❌ Critical DB/Model Failure: {e}")
        return

    # 2. Forex Controller (Years & Grid)
    try:
        from controllers.forex_controller import ForexController
        fc = ForexController()
        
        # Test Years
        years = fc.get_active_years()
        print(f"✅ ForexController.get_active_years(): OK -> Found {len(years)} years")
        
        # Test Grid Logic
        cots = fc.get_cotizaciones()
        print(f"✅ ForexController.get_cotizaciones(): OK -> Found {len(cots)} records")
        
    except Exception as e:
        print(f"❌ ForexController Failure: {e}")
        traceback.print_exc()

    # 3. Period Service
    try:
        from services.period_service import PeriodService
        # Test Check Status (SAFE read)
        status = PeriodService.check_period_status(date.today())
        print(f"✅ PeriodService.check_period_status(): OK -> {status}")
    except Exception as e:
        print(f"❌ PeriodService Failure: {e}")
        traceback.print_exc()

    # 4. Catalogs Controller
    try:
        from controllers.catalogs_controller import CatalogsController
        cc = CatalogsController()
        
        # Test Inmuebles
        inms = cc.get_inmuebles()
        print(f"✅ CatalogsController.get_inmuebles(): OK -> Found {len(inms)} items")
        
        # Test Proveedores
        provs = cc.get_proveedores()
        print(f"✅ CatalogsController.get_proveedores(): OK -> Found {len(provs)} items")
        
    except Exception as e:
        print(f"❌ CatalogsController Failure: {e}")
        traceback.print_exc()

    print("\n🏁 VERIFICATION COMPLETE")

if __name__ == "__main__":
    run_tests()
