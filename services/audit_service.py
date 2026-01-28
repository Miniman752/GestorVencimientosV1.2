from datetime import datetime
from database import SessionLocal
from models.entities import AuditLog
from utils.logger import app_logger

class AuditService:
    def log(self, module: str, action: str, entity_id: str = None, old_value: str = None, new_value: str = None, details: str = None, user_id: str = "System"):
        """
        Registra una acción en el log de auditoría.
        """
        db = SessionLocal()
        try:
            # Pack extra info into details as columns missing in DB
            details_packed = f"[{module}] {details or ''}"
            if old_value or new_value:
                details_packed += f" | {old_value} -> {new_value}"

            log_entry = AuditLog(
                timestamp=datetime.now(),
                # module=module, # Not in DB
                action=action,
                entity_id=entity_id,
                # old_value=..., # Not in DB
                # new_value=..., # Not in DB
                details=details_packed[:255], # Truncate to fit
                user_id=user_id
            )
            db.add(log_entry)
            db.commit()
            return True
        except Exception as e:
            app_logger.error(f"Audit Log Failed: {e}")
            return False
        finally:
            db.close()

    def get_logs(self, module=None, entity_id=None, limit=50):
        db = SessionLocal()
        try:
            query = db.query(AuditLog)
            if module:
                query = query.filter(AuditLog.details.like(f"[{module}]%"))
            if entity_id:
                query = query.filter(AuditLog.entity_id == entity_id)
            
            return query.order_by(AuditLog.id.desc()).limit(limit).all()
        except Exception as e:
            app_logger.error(f"Audit Fetch Failed: {e}")
            return []
        finally:
            db.close()


