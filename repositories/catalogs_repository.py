from typing import List, Optional
from sqlalchemy.orm import joinedload
from models.entities import Inmueble, ProveedorServicio, Obligacion, EstadoInmueble
from repositories.base_repository import BaseRepository

class InmuebleRepository(BaseRepository[Inmueble]):
    def get_all_active(self) -> List[Inmueble]:
        # 'estado' column does not exist in Cloud DB. Returning all.
        return self.session.query(Inmueble).all()

    def get_by_alias(self, alias: str) -> Optional[Inmueble]:
        return self.session.query(Inmueble).filter(Inmueble.alias == alias).first()

class ProveedorRepository(BaseRepository[ProveedorServicio]):
    def get_all_active(self) -> List[ProveedorServicio]:
        return self.session.query(ProveedorServicio).all() # No active column

    def get_by_name(self, name: str) -> Optional[ProveedorServicio]:
        return self.session.query(ProveedorServicio).filter(ProveedorServicio.nombre_entidad == name).first()

class ObligacionRepository(BaseRepository[Obligacion]):
    def get_all_with_relations(self) -> List[Obligacion]:
        return self.session.query(Obligacion).options(
            joinedload(Obligacion.inmueble),
            joinedload(Obligacion.proveedor)
        ).all()


