from functools import wraps
from typing import Callable, Any
from sqlalchemy.exc import SQLAlchemyError
from database import SessionLocal
from utils.logger import app_logger
from utils.logger import app_logger
from utils.exceptions import AppDatabaseError, BaseAppError

def safe_transaction(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that manages a database session lifecycle.
    - Injects 'session' kwarg if expected.
    - Commits on success.
    - Rollbacks on failure.
    - Logs errors.
    - Closes session.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if function expects 'session'
        # For simplicity in this base implementation, we assume logic instantiates its own session
        # OR we inject it if we want to be fancy. 
        # But wait, looking at current codebase, controllers instantiate SessionLocal() inside methods.
        # We want to replace that.
        
        # New Pattern: The Service/Repo methods will accept a session, or we inject it here.
        # Let's support both: if 'session' is passed, use it (nested transaction), else create new.
        
        session = kwargs.get('session')
        created_session = False
        
        if not session:
            session = SessionLocal()
            created_session = True
            kwargs['session'] = session
            
        try:
            result = func(*args, **kwargs)
            if created_session:
                session.commit()
            return result
        except SQLAlchemyError as e:
            if created_session:
                session.rollback()
            app_logger.error(f"Database Transaction Failed in {func.__name__}: {str(e)}")
            raise AppDatabaseError(f"Error en operación de base de datos: {str(e)}", original_exception=e)
        except BaseAppError as e:
            if created_session:
                session.rollback()
            # Do not log as error, just re-raise. Or log as warning if needed.
            # app_logger.warning(f"Business Exception in {func.__name__}: {str(e)}")
            raise e
        except Exception as e:
            if created_session:
                session.rollback()
            app_logger.error(f"Unexpected Error in {func.__name__}: {str(e)}", exc_info=True)
            raise e
        finally:
            if created_session:
                session.close()
                
    return wrapper

def log_execution(func):
    """Simple decorator to log function entry and exit (debug level)."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        app_logger.debug(f"Executing: {func.__name__}")
        try:
            return func(*args, **kwargs)
        except Exception as e:
            app_logger.error(f"Failed: {func.__name__} - {e}")
            raise
    return wrapper


