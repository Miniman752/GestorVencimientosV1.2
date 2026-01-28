import os
import sys

def check_syntax(start_path):
    print(f"Scanning for syntax errors in {start_path}...")
    errors = []
    count = 0
    for root, dirs, files in os.walk(start_path):
        if ".venv" in root or "__pycache__" in root:
            continue
            
        for file in files:
            if file.endswith(".py"):
                count += 1
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                    compile(source, full_path, 'exec')
                except SyntaxError as e:
                    errors.append(f"❌ {full_path}: {e}")
                except Exception as e:
                    errors.append(f"⚠️ {full_path}: {e}")
    
    print(f"Scanned {count} files.")
    if errors:
        print(f"Found {len(errors)} issues:")
        for e in errors:
            print(e)
    else:
        print("✅ No syntax errors found.")

if __name__ == "__main__":
    check_syntax(os.getcwd())
