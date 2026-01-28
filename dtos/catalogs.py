from dataclasses import dataclass
from typing import Optional
from models.entities import CategoriaServicio, EstadoInmueble

@dataclass
class InmuebleCreateDTO:
    alias: str
    direccion: str
    tipo_propiedad: Optional[str] = "Otro"

@dataclass
class InmuebleUpdateDTO:
    alias: Optional[str] = None
    direccion: Optional[str] = None

@dataclass
class ProveedorCreateDTO:
    nombre_entidad: str
    categoria: CategoriaServicio
    frecuencia_defecto: str = "Mensual"

@dataclass
class ProveedorUpdateDTO:
    nombre_entidad: Optional[str] = None
    categoria: Optional[CategoriaServicio] = None

@dataclass
class ObligacionDTO:
    inmueble_id: int
    servicio_id: int
    numero_cliente_referencia: Optional[str] = None


