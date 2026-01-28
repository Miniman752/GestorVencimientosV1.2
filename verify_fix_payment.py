import sys
import os
import traceback

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from database import SessionLocal
    from models.entities import Vencimiento, EstadoVencimiento
    from services.vencimiento_service import VencimientoService
    from dtos.vencimiento import VencimientoUpdateDTO
    from datetime import date
    
    def verify():
        print("Starting verification...")
        session = SessionLocal()
        try:
            # 1. Find a Vencimiento to update (or create one if needed, but let's try to find first)
            # Find one that is PENDIENTE or already PAGADO
            venc = session.query(Vencimiento).filter(Vencimiento.is_deleted == 0).first()
            
            if not venc:
                print("No Vencimientos found. Cannot verify.")
                return
                
            print(f"Testing on Vencimiento ID: {venc.id}, Current State: {venc.estado}")
            
            service = VencimientoService()
            
            # 2. Update to PAGADO with specific amount
            test_amount = 9999.99
            test_date = date.today()
            
            print(f"Updating to PAGADO with amount {test_amount}...")
            
            dto = VencimientoUpdateDTO(
                estado="PAGADO",
                monto_pagado=test_amount,
                fecha_pago=test_date
            )
            
            service.update(venc.id, dto)
            
            # 3. Verify Persistence
            # Must query a NEW session to ensure DB persistence
            session.close()
            session = SessionLocal()
            
            venc_check = session.query(Vencimiento).get(venc.id)
            
            print(f"Reloaded Vencimiento {venc_check.id}. State: {venc_check.estado}")
            
            if venc_check.pagos:
                payment = venc_check.pagos[0]
                print(f"Payment Record Found. Amount: {payment.monto}")
                
                if abs(payment.monto - test_amount) < 0.01:
                    print("SUCCESS: Payment amount matched!")
                else:
                    print(f"FAILURE: Expected {test_amount}, got {payment.monto}")
            else:
                 print("FAILURE: No payment record found!")

        finally:
            session.close()

    if __name__ == "__main__":
        verify()

except Exception as e:
    print("CRITICAL ERROR during script execution:")
    traceback.print_exc()
