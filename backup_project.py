import zipfile
import os
from datetime import datetime

def backup_project():
    # Use parent directory or current? zip file will be placed in current dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"Respaldo_Gestor_Vencimientos_{timestamp}.zip"
    
    current_dir = os.getcwd()
    
    # Exclusions
    excludes = {'.venv', 'venv', '__pycache__', '.git', '.idea', '.vscode'}
    
    print(f"Iniciando respaldo en: {zip_filename}")
    print(f"Directorio base: {current_dir}")
    
    count = 0
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(current_dir):
            # Modify dirs in-place to skip excluded paths
            dirs[:] = [d for d in dirs if d not in excludes]
            
            for file in files:
                if file == zip_filename: continue # Don't zip self
                if file.endswith(".pyc"): continue
                
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, current_dir)
                
                try:
                    zipf.write(file_path, arcname)
                    count += 1
                    if count % 100 == 0:
                        print(f"Comprimidos {count} archivos...", end='\r')
                except Exception as e:
                    print(f"Error zipping {file}: {e}")

    print(f"\nRespaldo Completado Exitosamente: {zip_filename}")
    print(f"Total archivos: {count}")

if __name__ == "__main__":
    backup_project()
