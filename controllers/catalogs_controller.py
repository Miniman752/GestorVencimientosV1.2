from typing import List
from models.entities import Inmueble, ProveedorServicio, EstadoInmueble
from services.catalogs_service import CatalogService, ObligacionService
from dtos.catalogs import InmuebleCreateDTO, InmuebleUpdateDTO, ProveedorCreateDTO, ProveedorUpdateDTO
from utils.logger import app_logger

class CatalogsController:
    def __init__(self):
        self.service = CatalogService()
        self.obl_service = ObligacionService()

    # --- Inmuebles ---
    def get_inmuebles(self, include_inactive=False) -> List[Inmueble]:
        return self.service.get_inmuebles(include_inactive)

    def create_inmueble(self, data: dict) -> bool:
        try:
            dto = InmuebleCreateDTO(
                alias=data['alias'],
                direccion=data['direccion'],
                tipo_propiedad=data.get('tipo_propiedad')
            )
            self.service.create_inmueble(dto)
            return True
        except Exception as e:
            app_logger.error(f"Controller Error Create Inmueble: {e}")
            raise e

    def update_inmueble(self, id: int, data: dict) -> bool:
        try:
            dto = InmuebleUpdateDTO(
                alias=data.get('alias'),
                direccion=data.get('direccion')
            )
            self.service.update_inmueble(id, dto)
            return True
        except Exception as e:
            app_logger.error(f"Controller Error Update Inmueble: {e}")
            raise e

    def delete_inmueble(self, id: int) -> bool:
        try:
            return self.service.delete_inmueble(id)
        except Exception as e:
            app_logger.error(f"Controller Error Delete Inmueble: {e}")
            raise e

    # --- Proveedores ---
    def get_proveedores(self, include_inactive=False) -> List[ProveedorServicio]:
        return self.service.get_proveedores(include_inactive)

    def create_proveedor(self, data: dict) -> bool:
        try:
            # Map enum if necessary or pass directly if view sends generic
            dto = ProveedorCreateDTO(
                nombre_entidad=data['nombre'],
                categoria=data['categoria'],
                frecuencia_defecto=data.get('frecuencia', 'Mensual')
            )
            self.service.create_proveedor(dto)
            return True
        except Exception as e:
            app_logger.error(f"Controller Error Create Proveedor: {e}")
            raise e

    def update_proveedor(self, id: int, data: dict) -> bool:
        try:
            dto = ProveedorUpdateDTO(
                nombre_entidad=data.get('nombre'),
                categoria=data.get('categoria')
            )
            self.service.update_proveedor(id, dto)
            return True
        except Exception as e:
            app_logger.error(f"Controller Error Update Proveedor: {e}")
            raise e

    def delete_proveedor(self, id: int) -> bool:
        try:
            return self.service.delete_proveedor(id)
        except AppValidationError as e:
            app_logger.warning(f"Validation Error Delete Proveedor: {e}")
            raise e
        except Exception as e:
            app_logger.error(f"Controller Error Delete Proveedor: {e}")
            raise e

    # --- Obligaciones (Services) ---
    # --- Obligaciones (Services) ---
    def create_obligacion(self, data: dict) -> bool:
        try:
            return self.obl_service.create(data)
        except Exception as e:
            app_logger.error(f"Error creating obligacion: {e}")
            raise e

    def delete_obligacion(self, id: int) -> bool:
        try:
            return self.obl_service.delete(id)
        except Exception as e:
            app_logger.error(f"Error deleting obligacion: {e}")
            raise e

    def update_obligacion_rule(self, id: int, tipo_ajuste_str: str) -> bool:
        try:
            return self.obl_service.update_rule(id, tipo_ajuste_str)
        except Exception as e:
            app_logger.error(f"Error updating rule: {e}")
            raise e


