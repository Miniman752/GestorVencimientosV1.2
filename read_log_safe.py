
import sys

def read_file_safe(path):
    print(f"--- READING {path} ---")
    try:
        with open(path, 'r', encoding='utf-16-le') as f:
            content = f.read()
            print(content[:2000]) # First 2000 chars
            if "UndefinedColumn" in content:
                print("\n\nFOUND UNDEFINED COLUMN ERROR:")
                start = content.find("UndefinedColumn")
                print(content[start:start+500])
    except Exception as e:
        print(f"Error reading utf-16-le: {e}")
        try:
             with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(content[:2000])
        except Exception as e2:
             print(f"Error reading utf-8: {e2}")

if __name__ == "__main__":
    read_file_safe("run_log_final.txt")
