
import sys
import os

# Ensure src_restored is in pythonpath
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from controllers.catalogs_controller import CatalogsController

def test_persistence():
    print("--- Test Field Persistence ---")
    ctl = CatalogsController()
    
    # 1. Setup
    alias = "PersistenceCheck"
    print(f"Creating '{alias}'...")
    
    # Cleanup first
    existing = [i for i in ctl.get_inmuebles(True) if i.alias == alias]
    for e in existing: ctl.delete_inmueble(e.id)
    
    ctl.create_inmueble({
        "alias": alias,
        "direccion": "Original Address",
        "titular": "Original Owner",
        "tipo_propiedad": "Casa"
    })
    
    target = next((i for i in ctl.get_inmuebles(True) if i.alias == alias), None)
    if not target:
        print("Setup failed.")
        return

    # 2. Update Basic Fields
    print("Updating Address and Owner...")
    new_addr = "New Address 123"
    new_owner = "New Owner ABC"
    
    update_data = {
        "alias": alias, # Keep same
        "direccion": new_addr,
        "titular": new_owner,
        # Estado not sent (should stay active)
    }
    
    try:
        ctl.update_inmueble(target.id, update_data)
        print("Update executed.")
    except Exception as e:
        print(f"Update threw exception: {e}")
        return

    # 3. Verify
    # Fetch FRESH
    target_post = next((i for i in ctl.get_inmuebles(True) if i.id == target.id), None)
    
    print(f"Original Addr: 'Original Address'")
    print(f"Current Addr:  '{target_post.direccion}'")
    print(f"Original Owner: 'Original Owner'")
    print(f"Current Owner:  '{target_post.titular}'")
    
    success = True
    if target_post.direccion != new_addr:
        print("FAILURE: Address was not updated.")
        success = False
    
    if target_post.titular != new_owner:
        print("FAILURE: Owner was not updated.")
        success = False
        
    if success:
        print("SUCCESS: All fields persisted correctly.")
    
    # Cleanup
    ctl.delete_inmueble(target.id)

if __name__ == "__main__":
    test_persistence()
