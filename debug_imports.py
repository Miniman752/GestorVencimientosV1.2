
import sys
from pathlib import Path
BASE_DIR = Path(r"e:\44.Gestos Vencimientos (PostgreSQL)")
sys.path.append(str(BASE_DIR))

try:
    print("Importing models...")
    from models.entities import CategoriaServicio, EstadoVencimiento
    print("Success models.")
    
    print("Importing DTOs...")
    from dtos.catalogs import InmuebleCreateDTO
    print("Success DTOs.")
    
    print("Importing Services...")
    from services.catalogs_service import CatalogService
    print("Success Services.")
except Exception as e:
    import traceback
    traceback.print_exc()
