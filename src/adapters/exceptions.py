class AdapterBaseException(Exception):
    """Base exception for all adapter-level errors."""
    pass

class SessionInvalidException(AdapterBaseException):
    """Raised when an operation is attempted on an invalid or uninitialized session."""
    pass

class ImportFailedException(AdapterBaseException):
    """Raised when the core compiler fails to import sources."""
    pass

class CompilationFailedException(AdapterBaseException):
    """Raised when the core compiler fails during the compilation phase."""
    pass
