from typing import List
from models.entities import Obligacion
from services.catalogs_service import ObligacionService
from utils.logger import app_logger

class ObligacionesController:
    def __init__(self):
        self.service = ObligacionService()

    def get_all_obligaciones(self) -> List[Obligacion]:
        """Retorna todas las obligaciones para usar en dropdowns (Alias Inmueble + Servicio)."""
        try:
            return self.service.get_all_detailed()
        except Exception as e:
            app_logger.error(f"Controller Error Get All Obligaciones: {e}")
            return []

    def get_or_create_default(self, inmueble_id: int) -> Obligacion:
        try:
            return self.service.create_default_for_inmueble(inmueble_id)
        except Exception as e:
            app_logger.error(f"Error creating default obligacion: {e}")
            return None


