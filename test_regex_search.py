from database import SessionLocal
from models.entities import Vencimiento, Obligacion, Inmueble, ProveedorServicio
from sqlalchemy import or_, text

session = SessionLocal()
try:
    search = "abl"
    search_regex = f"\\m{search}"
    print(f"Testing search for '{search}' with '{search_regex}'")
    
    query = session.query(Vencimiento).join(Obligacion).join(ProveedorServicio).join(Inmueble).filter(
        or_(
            ProveedorServicio.nombre_entidad.op('~*')(search_regex),
            Inmueble.alias.op('~*')(search_regex)
        )
    )
    
    results = query.all()
    print(f"Found {len(results)} items.")
    for r in results:
        print(f"- Provider: {r.obligacion.proveedor.nombre_entidad} | Inmueble: {r.obligacion.inmueble.alias}")

finally:
    session.close()
