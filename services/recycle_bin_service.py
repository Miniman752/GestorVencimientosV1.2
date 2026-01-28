from sqlalchemy.orm import joinedload
from database import SessionLocal
from models.entities import Vencimiento, Pago, Obligacion
from utils.decorators import safe_transaction

class RecycleBinService:
    @staticmethod
    @safe_transaction
    def get_deleted_vencimientos(session=None) -> list:
        """Fetch all Vencimientos marked as deleted."""
        return session.query(Vencimiento).options(
            joinedload(Vencimiento.obligacion).joinedload(Obligacion.proveedor),
            joinedload(Vencimiento.obligacion).joinedload(Obligacion.inmueble)
        ).filter(Vencimiento.is_deleted == 1).order_by(Vencimiento.fecha_vencimiento.desc()).all()

    @staticmethod
    @safe_transaction
    def restore_vencimiento(venc_id: int, session=None) -> bool:
        """Revive a record (Zombie antidote)."""
        venc = session.query(Vencimiento).get(venc_id)
        if venc:
            venc.is_deleted = 0
            session.add(venc)
            return True
        return False

    @staticmethod
    @safe_transaction
    def hard_delete_vencimiento(venc_id: int, session=None) -> bool:
        """
        Permanently purge a record.
        WARNING: This also deletes associated Payments if Cascade is on, 
        or we must handle them manually.
        """
        venc = session.query(Vencimiento).get(venc_id)
        if venc:
            # Manual check for Payments to warn?
            # Ideally we rely on DB cascade, but let's be safe and delete them explicitly if exists
            session.query(Pago).filter(Pago.vencimiento_id == venc_id).delete()
            
            session.delete(venc)
            return True
        return False
