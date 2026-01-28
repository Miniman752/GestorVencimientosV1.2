from dataclasses import dataclass
from datetime import date
from typing import Optional
from models.entities import EstadoVencimiento

@dataclass
class VencimientoCreateDTO:
    obligacion_id: int
    periodo: str
    fecha_vencimiento: date
    monto_original: float
    estado: EstadoVencimiento = EstadoVencimiento.PENDIENTE
    ruta_archivo_pdf: Optional[str] = None
    ruta_comprobante_pago: Optional[str] = None
    documento_id: Optional[int] = None
    comprobante_pago_id: Optional[int] = None
    
@dataclass
class VencimientoUpdateDTO:
    monto_original: Optional[float] = None
    fecha_vencimiento: Optional[date] = None
    obligacion_id: Optional[int] = None # Support re-linking
    estado: Optional[str] = None # Str to handle string input from UI, will convert in service
    estado_enum: Optional[EstadoVencimiento] = None
    periodo: Optional[str] = None # Allow manual period override

    
    new_file_path: Optional[str] = None
    new_payment_path: Optional[str] = None
    
    monto_pagado: Optional[float] = None
    fecha_pago: Optional[date] = None
    
    documento_id: Optional[int] = None
    comprobante_pago_id: Optional[int] = None









