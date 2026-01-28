import os
import importlib.util
import sys

def check_imports(start_dir):
    print(f"Checking imports in {start_dir}...")
    for root, dirs, files in os.walk(start_dir):
        for file in files:
            if file.endswith(".py") and file != "main.py" and file != "check_all_imports.py":
                path = os.path.join(root, file)
                module_name = path.replace(start_dir + os.sep, "").replace(os.sep, ".").replace(".py", "")
                
                try:
                    # Skip some specific ones if needed, but let's try all
                    print(f"Testing {module_name}...", end=" ")
                    
                    # Manual import
                    spec = importlib.util.spec_from_file_location(module_name, path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                        print("OK")
                    else:
                        print("SKIPPED (No Spec)")
                except Exception as e:
                    print(f"FAIL: {e}")
                    # We continue to find more errors

if __name__ == "__main__":
    check_imports(os.getcwd())
