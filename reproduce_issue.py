from services.forex_service import ForexService
from models.entities import Moneda
from datetime import date
from unittest.mock import MagicMock

def test_conversion_bug():
    service = ForexService()
    # Mocking get_rate to ensure we don't depend on DB
    service.get_rate = MagicMock(return_value=1000.0)
    
    amount = 1000.0
    from_curr = Moneda.ARS
    to_curr = "USD"
    date_ref = date.today()
    session = MagicMock()
    
    result = service.convert(amount, from_curr, to_curr, date_ref, session)
    
    print(f"Amount: {amount} ARS")
    print(f"Target: {to_curr}")
    print(f"Rate: 1000.0")
    print(f"Result: {result}")
    
    if result == 1.0:
        print("SUCCESS: Conversion worked (1000/1000)")
    elif result == 1000.0:
        print("FAILURE: Returned original amount (Bug confirmed)")
    else:
        print(f"UNKNOWN: {result}")

if __name__ == "__main__":
    test_conversion_bug()
