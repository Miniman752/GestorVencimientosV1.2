
import sys
import os

# Ensure src_restored is in pythonpath
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from controllers.catalogs_controller import CatalogsController
from models.entities import EstadoInmueble

def test_alias_update():
    print("--- Test Alias Update (Case Insensitivity & Self-Check) ---")
    ctl = CatalogsController()
    
    # 1. Create Inmueble
    alias_original = "TestAliasCase"
    data_create = {
        "alias": alias_original,
        "direccion": "Address A",
        "titular": "Owner A",
        "tipo_propiedad": "Casa"
    }
    
    # Clean up previous runs if enabled
    existing = [i for i in ctl.get_inmuebles(True) if i.alias.lower() == alias_original.lower()]
    for e in existing: ctl.delete_inmueble(e.id)
    
    print(f"Creating '{alias_original}'...")
    ctl.create_inmueble(data_create)
    
    inmuebles = ctl.get_inmuebles(True)
    target = next((i for i in inmuebles if i.alias == alias_original), None)
    if not target:
        print("Failed to create test subject.")
        return

    # 2. Update with SAME alias (Should PASS now, previously might fail if logic was flawed)
    print("Test 1: Updating with EXACT same alias...")
    try:
        ctl.update_inmueble(target.id, {"alias": alias_original, "direccion": "Addr Modified"})
        print("PASS: Same alias update allowed.")
    except Exception as e:
        print(f"FAIL: Same alias update blocked: {e}")

    # 3. Update with CASE DIFFERENCE (e.g. "testaliascase")
    # This should be allowed as "same entity", but if logic is "if alias != item.alias check_exists", 
    # then "test" != "Test" -> checks exists -> finds "Test" -> Error if not excluding self.
    print(f"Test 2: Updating with case change ('{alias_original.upper()}')")
    try:
        ctl.update_inmueble(target.id, {"alias": alias_original.upper()})
        print("PASS: Case-variant alias update allowed (Self-match handled).")
    except Exception as e:
        print(f"FAIL: Case-variant alias update blocked: {e}")
        
    print("Cleaning up...")
    ctl.delete_inmueble(target.id)

if __name__ == "__main__":
    test_alias_update()
