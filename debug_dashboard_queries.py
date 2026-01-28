from database import SessionLocal
from models.entities import Vencimiento, Obligacion, ProveedorServicio, Inmueble, EstadoVencimiento
from sqlalchemy import func, extract
from datetime import date

session = SessionLocal()
today = date.today()
current_year = today.year

with open("debug_output.txt", "w", encoding="utf-8") as f:
    f.write(f"Debug Date: {today}\n")
    f.write(f"Current Year: {current_year}\n")

    # 1. Category Query
    f.write("\n--- QUERY 1: Category ---\n")
    try:
        cat_groups = session.query(
            ProveedorServicio.categoria, 
            Vencimiento.moneda, 
            func.sum(Vencimiento.monto_original)
        ).select_from(Vencimiento).join(Obligacion).join(ProveedorServicio).filter(
            extract('year', Vencimiento.fecha_vencimiento) == current_year
        ).filter(
            Vencimiento.is_deleted == 0
        ).group_by(
            ProveedorServicio.categoria, Vencimiento.moneda
        ).all()
        
        f.write(f"Result Count: {len(cat_groups)}\n")
        for row in cat_groups:
            f.write(f"{row}\n")
    except Exception as e:
        f.write(f"ERROR Query 1: {e}\n")

    # 2. Top Properties Query - Current Month
    f.write("\n--- QUERY 2: Top Properties (Month) ---\n")
    try:
        top_groups = session.query(
            Inmueble.alias, 
            Vencimiento.moneda, 
            func.sum(Vencimiento.monto_original)
        ).select_from(Vencimiento).join(Obligacion).join(Inmueble).filter(
            extract('month', Vencimiento.fecha_vencimiento) == today.month, 
            extract('year', Vencimiento.fecha_vencimiento) == current_year
        ).filter(
            Vencimiento.is_deleted == 0
        ).group_by(
            Inmueble.alias, Vencimiento.moneda
        ).all()
        f.write(f"Result Count: {len(top_groups)}\n")
        for row in top_groups:
            f.write(f"{row}\n")
    except Exception as e:
        f.write(f"ERROR Query 2: {e}\n")

    # 3. Check Vencimientos Count
    f.write("\n--- DEBUG: Total Vencimientos 2026 ---\n")
    count = session.query(Vencimiento).filter(extract('year', Vencimiento.fecha_vencimiento) == current_year).count()
    f.write(f"Total Vencimientos Year {current_year}: {count}\n")

    count_month = session.query(Vencimiento).filter(
        extract('year', Vencimiento.fecha_vencimiento) == current_year,
        extract('month', Vencimiento.fecha_vencimiento) == today.month
    ).count()
    f.write(f"Total Vencimientos Month {today.month}/{current_year}: {count_month}\n")

    # 4. Check Enums
    f.write("\n--- DEBUG: Enum Handling ---\n")
    prov = session.query(ProveedorServicio).first()
    if prov:
        f.write(f"Example Proveedor: {prov.nombre_entidad}, Cat: {prov.categoria} (Type: {type(prov.categoria)})\n")
    else:
        f.write("No proveedores found.\n")
