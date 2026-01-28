import os
import zipfile
import datetime

def create_backup():
    # Configuration
    source_dir = os.getcwd()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    zip_filename = f"GestorVencimientos_FullBackup_{timestamp}.zip"
    
    # Exclusion rules
    # Exclusion rules
    excluded_dirs = {'.venv', '__pycache__', '.git', 'dist', 'build', 'backups'}
    
    # Exclude typical dev trash and existing zips to avoid recursion
    excluded_extensions = {'.pyc'}
    excluded_files_substrings = {'.zip'} # Exclude all other zips

    print(f"Starting backup of {source_dir}...")
    print(f"Target file: {zip_filename}")

    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                # Filter directories in-place
                dirs[:] = [d for d in dirs if d not in excluded_dirs]
                
                for file in files:
                    if file == zip_filename: continue # Don't zip self
                    
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, source_dir)
                    
                    # Extension check
                    if any(file.endswith(ext) for ext in excluded_extensions):
                        continue
                        
                    # Substring check (e.g., exclude all other .zip files to prevent nesting)
                    if any(sub in file for sub in excluded_files_substrings):
                        continue
                        
                    print(f"Zipping: {rel_path}")
                    zipf.write(file_path, rel_path)
                    
        print(f"✅ Backup created successfully: {os.path.abspath(zip_filename)}")
        print(f"Size: {os.path.getsize(zip_filename) / (1024*1024):.2f} MB")
        
    except Exception as e:
        print(f"❌ Error creating backup: {e}")

if __name__ == "__main__":
    create_backup()
