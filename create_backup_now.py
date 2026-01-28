import os
import zipfile
import datetime

def create_backup():
    # Setup Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(base_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"Backup_Gestor_Vencimientos_{timestamp}.zip"
    zip_path = os.path.join(backup_dir, zip_filename)
    
    print(f"Starting Backup to: {zip_path}")
    
    # Exclusions
    exclude_dirs = {
        '.venv', '__pycache__', 'backups', 'dist', 'build', 
        'installers', '.git', '.idea', '.vscode'
    }
    exclude_extensions = {'.zip', '.exe', '.pyc', '.log'}
    
    file_count = 0
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                # Skip heavy extensions or logs
                _, ext = os.path.splitext(file)
                if ext.lower() in exclude_extensions:
                    continue
                    
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, base_dir)
                
                print(f"Adding: {rel_path}")
                zipf.write(file_path, rel_path)
                file_count += 1
                
    print("-" * 30)
    print(f"Backup Complete!")
    print(f"File: {zip_path}")
    print(f"Total Files: {file_count}")

if __name__ == "__main__":
    create_backup()
