class BaseAppError(Exception):
    """Base class for application exceptions."""
    pass

class ServiceError(BaseAppError):
    """Raised when a service operation fails."""
    pass

class PeriodLockedError(BaseAppError):
    """Raised when attempting to modify data in a locked fiscal period."""
    pass

class AppDatabaseError(BaseAppError):
    """Raised when a database error occurs."""
    def __init__(self, message, original_exception=None):
        super().__init__(message)
        self.original_exception = original_exception

class AppValidationError(BaseAppError):
    """Raised when validation fails."""
    pass

class PlatformError(BaseAppError):
    """Raised when platform-specific operations fail."""
    pass

class AppIntegrityError(BaseAppError):
    """Raised when an operation violates data integrity rules."""
    pass


