from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from database import SessionLocal
from models.entities import PeriodoContable, EstadoPeriodo, Vencimiento
from utils.exceptions import PeriodLockedError, AppIntegrityError
from utils.logger import app_logger
from utils.decorators import safe_transaction

class PeriodService:
    @staticmethod
    def get_period_id(dt: date) -> str:
        """Returns 'YYYY-MM' from a date."""
        return dt.strftime("%Y-%m")

    @staticmethod
    def is_year_active(year: int, session: Session) -> bool:
        from models.entities import YearConfig
        # Default to True if no config exists? Or Strict?
        # User wants strict. Let's assume if table empty, maybe allow? 
        # But if table has rows, enforce.
        # Actually safer: If record exists, check is_active. If not exists, assume INACTIVE or ACTIVE?
        # Usually defaults to Open. Let's check if record exists.
        yc = session.query(YearConfig).get(year)
        if yc:
            return yc.is_active == 1
        return True # Default to open if not configured, to avoid locking out.

    @staticmethod
    def ensure_period_exists(period_id: str, session: Session, auto_create: bool = False) -> Optional[PeriodoContable]:
        """Gets a Period record. Optional auto-create."""
        p = session.query(PeriodoContable).filter_by(periodo_id=period_id).first()
        if not p and auto_create:
            # Validate Year first
            y = int(period_id.split('-')[0])
            if not PeriodService.is_year_active(y, session):
                 return None # Block creation if year inactive
                 
            p = PeriodoContable(periodo_id=period_id, estado=EstadoPeriodo.ABIERTO.value)
            session.add(p)
        return p

    @staticmethod
    @safe_transaction
    def check_period_status(target_date: date, session=None):
        """
        Checks if the period is writable.
        Returns: EstadoPeriodo or None
        """
        if not target_date: return EstadoPeriodo.ABIERTO
        
        pid = PeriodService.get_period_id(target_date)
        
        # STRICT: Do not auto-create just by checking status
        p = PeriodService.ensure_period_exists(pid, session, auto_create=False)
        
        if not p:
            # If it doesn't exist, is it writable?
            # Creating a record strictly requires 'create_period'.
            # But checking status for a "New Vencimiento" dialog?
            # If we say it's OPEN, the flow proceeds.
            # But we want to ensure the YEAR is active at least.
            if not PeriodService.is_year_active(target_date.year, session):
                raise PeriodLockedError(f"El año fiscal {target_date.year} no está habilitado.")
            return EstadoPeriodo.ABIERTO # Virtual Open
            
        state_val = p.estado.value if hasattr(p.estado, 'value') else str(p.estado)
        if state_val == EstadoPeriodo.BLOQUEADO.value:
            raise PeriodLockedError(f"El período {pid} está BLOQUEADO.")
            
        return next((e for e in EstadoPeriodo if e.value == state_val), state_val)

    @staticmethod
    @safe_transaction
    def create_period(year: int, month: int, session: Session = None):
        """Creates a new period explicitly."""
        # 1. Check Year Config
        if not PeriodService.is_year_active(year, session):
             raise ValueError(f"El año fiscal {year} no está activo o habilitado.")

        period_id = f"{year}-{month:02d}"
        if session.query(PeriodoContable).filter_by(periodo_id=period_id).first():
            raise ValueError(f"El período {period_id} ya existe.")
        
        p = PeriodoContable(periodo_id=period_id, estado=EstadoPeriodo.ABIERTO.value)
        session.add(p)
        return p

    @staticmethod
    @safe_transaction
    def update_period(period_id: str, status: EstadoPeriodo, notes: str = None, user: str = None, session=None):
        p = session.query(PeriodoContable).filter_by(periodo_id=period_id).first()
        if not p: raise ValueError("Período no encontrado")
        
        p.estado = status.value if hasattr(status, 'value') else str(status)
        if notes is not None: p.notas = notes
        if notes is not None: p.notas = notes
        # if user is not None: p.usuario_responsable = user # Field missing in DB model
        
        if status != EstadoPeriodo.ABIERTO and not p.fecha_cierre:
            p.fecha_cierre = date.today()
        elif status == EstadoPeriodo.ABIERTO:
             p.fecha_cierre = None
            
        return True

    @staticmethod
    @safe_transaction
    def delete_period(period_id: str, force: bool = False, session=None):
        # 1. Integrity Check (Active Records Only)
        if not force:
            count = session.query(Vencimiento).filter_by(periodo=period_id).filter(Vencimiento.is_deleted == 0).count()
            if count > 0:
                raise AppIntegrityError(f"No se puede eliminar el período {period_id} porque tiene {count} vencimientos asociados.")
        
        # 2. Cleanup Dependencies (Pagos & Vencimientos including Deleted ones)
        # Fetch IDs to delete from Pagos
        venc_ids = session.query(Vencimiento.id).filter_by(periodo=period_id).all()
        ids_list = [v.id for v in venc_ids]
        
        if ids_list:
            # Delete Pagos
            from models.entities import Pago
            session.query(Pago).filter(Pago.vencimiento_id.in_(ids_list)).delete(synchronize_session=False)
            
            # Delete Vencimientos (Trash)
            session.query(Vencimiento).filter(Vencimiento.id.in_(ids_list)).delete(synchronize_session=False)

        # 3. Delete Period Record
        p = session.query(PeriodoContable).filter_by(periodo_id=period_id).first()
        if p:
            session.delete(p)
            return True
        return False

    @staticmethod
    @safe_transaction
    def get_all_periods(session=None):
        return session.query(PeriodoContable).order_by(PeriodoContable.periodo_id.desc()).all()


