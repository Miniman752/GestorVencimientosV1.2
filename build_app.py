import os
import shutil
import subprocess
import sys
import time

def clean():
    print("🧹 Cleaning previous build artifacts...")
    for d in ["build", "dist"]:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
                print(f"   - Removed {d}/")
            except Exception as e:
                print(f"   - Error removing {d}/: {e}")

def build():
    print("🚀 Starting PyInstaller Build...")
    spec_file = "GestorVencimientos.spec"
    
    if not os.path.exists(spec_file):
        print(f"❌ Error: Spec file '{spec_file}' not found.")
        sys.exit(1)

    cmd = [sys.executable, "-m", "PyInstaller", spec_file, "--clean", "--noconfirm"]
    
    start_time = time.time()
    res = subprocess.run(cmd, capture_output=False)
    duration = time.time() - start_time
    
    if res.returncode != 0:
        print("❌ Build Failed!")
        sys.exit(1)
    
    print(f"✅ Build Success! (Took {duration:.2f}s)")
    print(f"   - Executable should be in 'dist/' folder.")

def check_imports():
    print("🔍 Pre-flight verify of imports...")
    # Optional: Run check_imports_runtime.py if exists
    if os.path.exists("check_imports_runtime.py"):
         subprocess.run([sys.executable, "check_imports_runtime.py"])

if __name__ == "__main__":
    # check_imports() 
    clean()
    build()
