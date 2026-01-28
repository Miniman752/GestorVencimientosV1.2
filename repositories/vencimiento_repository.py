from typing import List, Optional
from sqlalchemy.orm import joinedload
from models.entities import Vencimiento, Obligacion
from repositories.base_repository import BaseRepository
from config import FILTER_ALL_OPTION

class VencimientoRepository(BaseRepository[Vencimiento]):
    def get_details_all(self, inmueble_id=None, estado=None, period_id=None, limit=None, offset=None) -> tuple[List[Vencimiento], int]:
        """Get vencimientos with joined relationships. Returns (items, total_count)."""

        query = self.session.query(Vencimiento).options(
            joinedload(Vencimiento.obligacion).joinedload(Obligacion.inmueble),
            joinedload(Vencimiento.obligacion).joinedload(Obligacion.proveedor),
            joinedload(Vencimiento.pagos),
            joinedload(Vencimiento.documento),
            joinedload(Vencimiento.comprobante_pago)
        )

        if period_id:
             query = query.filter(Vencimiento.periodo == period_id)
        
        if inmueble_id and inmueble_id != FILTER_ALL_OPTION:
             query = query.join(Obligacion).filter(Obligacion.inmueble_id == inmueble_id)
            
        if estado and estado != FILTER_ALL_OPTION:
            query = query.filter(Vencimiento.estado == estado)

        # Default Filter: Hide Deleted
        query = query.filter(Vencimiento.is_deleted == 0)
            
        total_count = query.count()
        
        # Apply Sorting default (Date DESC)
        query = query.order_by(Vencimiento.fecha_vencimiento.desc())
        
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
            
        return query.all(), total_count
    
    def get_with_relations(self, id: int) -> Optional[Vencimiento]:
        return self.session.query(Vencimiento).options(
            joinedload(Vencimiento.obligacion).joinedload(Obligacion.inmueble),
            joinedload(Vencimiento.obligacion).joinedload(Obligacion.proveedor),
            joinedload(Vencimiento.pagos),
            joinedload(Vencimiento.documento),
            joinedload(Vencimiento.comprobante_pago)
        ).get(id)


