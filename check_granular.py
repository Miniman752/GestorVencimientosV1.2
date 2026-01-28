import sys
import os
import importlib
import pkgutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

PACKAGES = ['models', 'dtos', 'utils', 'repositories', 'services', 'controllers', 'views']

def check_all():
    print("START SCAN")
    for pkg_name in PACKAGES:
        pkg_path = os.path.join(BASE_DIR, pkg_name)
        if not os.path.exists(pkg_path): continue
        
        print(f"--- PACKAGE: {pkg_name} ---")
        try:
            importlib.import_module(pkg_name)
        except Exception as e:
            print(f"FAIL PKG {pkg_name}: {e}")
            
        for _, name, _ in pkgutil.walk_packages([pkg_path], prefix=f"{pkg_name}."):
            # Exclusions
            if "main_window" in name: continue
            
            try:
                importlib.import_module(name)
                # print(f"OK: {name}") # Quiet success
            except Exception as e:
                print(f"FAIL MOD {name}: {e}")
    print("END SCAN")

if __name__ == "__main__":
    check_all()
