
import sys
import os

# Ensure src_restored is in pythonpath
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from controllers.catalogs_controller import CatalogsController
from models.entities import EstadoInmueble

def test_update_inmueble():
    print("--- Test Update Inmueble ---")
    ctl = CatalogsController()
    
    # 1. Create a dummy inmueble
    print("Creating Inmueble...")
    data_create = {
        "alias": "TestInmueble_Repro",
        "direccion": "Calle 123",
        "titular": "Juan Perez",
        "tipo_propiedad": "Casa"
    }
    target = None
    try:
        ctl.create_inmueble(data_create)
        print("Inmueble created.")
    except Exception as e:
        print(f"Error creating: {e}")
        
    # Get ID
    inmuebles = ctl.get_inmuebles(include_inactive=True)
    target = next((i for i in inmuebles if i.alias == "TestInmueble_Repro"), None)
    
    if not target:
        print("ERROR: Inmueble not found after creation.")
        # Try finding it by loose match?
        return

    print(f"Original Status: {target.estado}")

    # 2. Try to update (Change alias and set to INACTIVE)
    print("Updating Inmueble (Alias -> 'TestInmueble_Repro_Updated', Estado -> INACTIVO)...")
    data_update = {
        "alias": "TestInmueble_Repro_Updated",
        "direccion": "Calle 123 Modified",
        "titular": "Juan Perez Modified",
        "estado": EstadoInmueble.INACTIVO
    }
    
    try:
        print(f"DEBUG: Passing estado={data_update['estado']} to ctl.update_inmueble")
        ctl.update_inmueble(target.id, data_update)
        print("DEBUG: update_inmueble returned.")
    except Exception as e:
        print(f"Error updating: {e}")
        
    # 3. Verify
    print("Fetching updated inmueble for verification...")
    # Force new instance logic if needed, but ctl.get_inmuebles should create new session
    inmuebles_post = ctl.get_inmuebles(include_inactive=True)
    target_post = next((i for i in inmuebles_post if i.id == target.id), None)
    
    if target_post:
        print(f"New Alias: {target_post.alias} (Expected: TestInmueble_Repro_Updated)")
        print(f"New Status: {target_post.estado} (Expected: {EstadoInmueble.INACTIVO})")
        
        if target_post.estado != EstadoInmueble.INACTIVO:
            print("FAILURE: Status was NOT updated!")
        else:
            print("SUCCESS: Status was updated.")
            
        # Clean up
        print("Cleaning up...")
        ctl.delete_inmueble(target.id)
    else:
        print("ERROR: Inmueble lost after update.")

if __name__ == "__main__":
    test_update_inmueble()
