import sys
import os
import importlib
import pkgutil

# Setup Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Modules to scan
PACKAGES = ['models', 'dtos', 'utils', 'repositories', 'services', 'controllers', 'views']

def check_imports():
    print("=== Runtime Import Integrity Check ===")
    errors = []
    success_count = 0
    
    for pkg_name in PACKAGES:
        pkg_path = os.path.join(BASE_DIR, pkg_name)
        if not os.path.exists(pkg_path):
            print(f"Skipping missing package: {pkg_name}")
            continue
            
        print(f"\nScanning package: {pkg_name}...")
        
        # 1. Import the package itself
        try:
            importlib.import_module(pkg_name)
            success_count += 1
        except Exception as e:
            errors.append(f"📦 PACKAGE ERROR {pkg_name}: {e}")
            continue

        # 2. Walk modules
        for _, name, _ in pkgutil.walk_packages([pkg_path], prefix=f"{pkg_name}."):
            try:
                # Skip some known problematics if necessary (e.g. view main loops)
                if "main_window" in name and pkg_name == 'views': 
                    continue
                
                importlib.import_module(name)
                print(f"  [OK] {name}")
                success_count += 1
            except Exception as e:
                errors.append(f"  [ERROR] MODULE ERROR {name}: {e}")

    print(f"\n{'='*40}")
    print(f"Scan Complete. Imported {success_count} modules.")
    if errors:
        print(f"Found {len(errors)} IMPORT ERRORS:")
        for e in errors:
            print(e)
    else:
        print("[OK] No import errors detected. Circular dependencies unlikely.")

if __name__ == "__main__":
    check_imports()
