from database import SessionLocal
from models.entities import Vencimiento, Obligacion, Inmueble, ProveedorServicio
from sqlalchemy import or_, text

session = SessionLocal()
try:
    search = "abl"
    search_regex = f"\\m{search}"
    
    # Check if 'Estudio Contable' matches
    test_val = session.execute(text(f"SELECT 'Estudio Contable' ~* '{search_regex}'")).scalar()
    print(f"Regex '{search_regex}' matches 'Estudio Contable'? {test_val}")

    test_val_abl = session.execute(text(f"SELECT 'ABL' ~* '{search_regex}'")).scalar()
    print(f"Regex '{search_regex}' matches 'ABL'? {test_val_abl}")
    
    test_val_imp = session.execute(text(f"SELECT 'Impuesto ABL' ~* '{search_regex}'")).scalar()
    print(f"Regex '{search_regex}' matches 'Impuesto ABL'? {test_val_imp}")

finally:
    session.close()
