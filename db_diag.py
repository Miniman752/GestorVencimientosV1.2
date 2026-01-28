from database import SessionLocal
from models.entities import Vencimiento, EstadoVencimiento, Inmueble, Obligacion, ProveedorServicio
from sqlalchemy import func

session = SessionLocal()
results = []
try:
    results.append(f"Total Vencimientos: {session.query(func.count(Vencimiento.id)).scalar()}")
    results.append(f"Is Deleted == 1: {session.query(func.count(Vencimiento.id)).filter(Vencimiento.is_deleted == 1).scalar()}")
    results.append(f"Is Deleted == 0: {session.query(func.count(Vencimiento.id)).filter(Vencimiento.is_deleted == 0).scalar()}")
    
    estados = session.query(Vencimiento.estado, func.count(Vencimiento.id)).group_by(Vencimiento.estado).all()
    results.append(f"Estados in DB: {estados}")
    
    # Test Dashboard Query logic
    total_deuda = session.query(func.sum(Vencimiento.monto_original)).filter(
        Vencimiento.is_deleted == 0,
        Vencimiento.estado.in_([EstadoVencimiento.PENDIENTE, EstadoVencimiento.VENCIDO, EstadoVencimiento.PROXIMO])
    ).scalar() or 0.0
    results.append(f"Dashboard Deuda Query Result: {total_deuda}")

    # Test Search Join
    search = "e" # Something common
    search_fmt = f"%{search}%"
    join_count = session.query(func.count(Vencimiento.id)).join(Vencimiento.obligacion)\
                         .join(ProveedorServicio, Obligacion.servicio_id == ProveedorServicio.id)\
                         .join(Inmueble, Obligacion.inmueble_id == Inmueble.id)\
                         .filter(ProveedorServicio.nombre_entidad.ilike(search_fmt)).scalar()
    results.append(f"Search Join count (search='e'): {join_count}")

    with open("diag_output.txt", "w") as f:
        f.write("\n".join(results))
    print("DONE")

finally:
    session.close()
