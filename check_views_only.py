import sys
import os
import importlib
import pkgutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

def check_views():
    pkg_path = os.path.join(BASE_DIR, 'views')
    print("Checking views...")
    for _, name, _ in pkgutil.walk_packages([pkg_path], prefix="views."):
        if "main_window" in name: continue
        try:
            importlib.import_module(name)
        except Exception as e:
            print(f"FAIL: {name} -> {e}")

if __name__ == "__main__":
    check_views()
