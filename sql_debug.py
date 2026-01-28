from database import SessionLocal
from models.entities import Vencimiento, EstadoVencimiento, Inmueble, Obligacion
from sqlalchemy import func
from sqlalchemy.orm import aliased

session = SessionLocal()
try:
    V = aliased(Vencimiento)
    O = aliased(Obligacion)
    I = aliased(Inmueble)
    
    query = session.query(
        I.alias, 
        func.count(V.id)
    ).join(O, I.id == O.inmueble_id)\
     .join(V, V.obligacion_id == O.id)\
     .filter(V.is_deleted == 0, V.estado != EstadoVencimiento.PAGADO)\
     .group_by(I.alias)
    
    print("QUERY SQL:")
    print(query.statement.compile(compile_kwargs={"literal_binds": True}))
    
finally:
    session.close()
