from database import SessionLocal, init_db
from models.entities import Inmueble, ProveedorServicio, Obligacion, Vencimiento, EstadoInmueble, CategoriaServicio, EstadoVencimiento
from datetime import date, timedelta
import random

def seed():
    # init_db() # REMOVED to avoid circular reset
    db = SessionLocal()
    
    # Check if data exists
    if db.query(Inmueble).count() > 0:
        print("Data already exists in Cloud DB. Skipping seed.")
        db.close()
        return

    # Limpiar datos existentes
    # Note: If we get here, Inmueble is empty. 
    # To be safe against orphaned records elsewhere, we should include Pago if we were doing a full wipe,
    # but since we are skipping if data exists, this is safer.
    db.query(Vencimiento).delete()
    db.query(Obligacion).delete()
    db.query(ProveedorServicio).delete()
    db.query(Inmueble).delete()
    db.commit()

    # Inmuebles
    inm1 = Inmueble(alias="Casa Centro", direccion="Av. Siempre Viva 123", tipo_propiedad="Casa")
    inm2 = Inmueble(alias="Depto Playa", direccion="Costanera 456", tipo_propiedad="Departamento")
    db.add_all([inm1, inm2])
    db.commit()

    # Proveedores
    prov1 = ProveedorServicio(nombre_entidad="Edesur", categoria=CategoriaServicio.SERVICIO)
    prov2 = ProveedorServicio(nombre_entidad="ARBA", categoria=CategoriaServicio.IMPUESTO)
    prov3 = ProveedorServicio(nombre_entidad="Expensas", categoria=CategoriaServicio.EXPENSA)
    db.add_all([prov1, prov2, prov3])
    db.commit()

    # Obligaciones
    obl1 = Obligacion(inmueble_id=inm1.id, servicio_id=prov1.id, numero_cliente_referencia="123456")
    obl2 = Obligacion(inmueble_id=inm2.id, servicio_id=prov2.id, numero_cliente_referencia="987654")
    db.add_all([obl1, obl2])
    db.commit()

    # Vencimientos (Generar para los ultimos 3 meses)
    vencimientos = []
    today = date.today()
    for i in range(3):
        fecha = today - timedelta(days=30*i)
        
        # Vencimiento 1
        v1 = Vencimiento(
            obligacion_id=obl1.id,
            periodo=fecha.strftime("%Y-%m"),
            fecha_vencimiento=fecha,
            monto_original=15000.0 + (i*500),
            estado=EstadoVencimiento.PENDIENTE if i == 0 else EstadoVencimiento.PAGADO
        )
        vencimientos.append(v1)

        # Vencimiento 2
        v2 = Vencimiento(
            obligacion_id=obl2.id,
            periodo=fecha.strftime("%Y-%m"),
            fecha_vencimiento=fecha + timedelta(days=5),
            monto_original=5000.0,
            estado=EstadoVencimiento.VENCIDO if i == 0 else EstadoVencimiento.PAGADO
        )
        vencimientos.append(v2)

    db.add_all(vencimientos)
    db.commit()
    print("Datos de prueba insertados correctamente.")
    db.close()

# if __name__ == "__main__":
#     seed()