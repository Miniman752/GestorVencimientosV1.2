import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from models.entities import EstadoPeriodo, Cotizacion
    print("Imports successful.")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

# Check EstadoPeriodo
try:
    if EstadoPeriodo.BLOQUEADO:
        print("EstadoPeriodo.BLOQUEADO exists.")
except AttributeError:
    print("FAIL: EstadoPeriodo.BLOQUEADO missing.")
    sys.exit(1)

# Check Cotizacion
try:
    c = Cotizacion(compra=1.0)
    print("Cotizacion instantiated with compra.")
except TypeError as e:
    print(f"FAIL: Cotizacion instantiation failed: {e}")
    sys.exit(1)

print("VERIFICATION SUCCESSFUL")
