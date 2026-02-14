from typing import Any, Optional, Dict

class VoiceNoteError(Exception):
    """Base exception for all VoiceNote API errors."""
    def __init__(
        self, 
        message: str, 
        code: str = "INTERNAL_ERROR", 
        status_code: int = 500,
        detail: Optional[Any] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)

class AuthenticationError(VoiceNoteError):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed", detail: Optional[Any] = None):
        super().__init__(message, code="AUTH_ERROR", status_code=401, detail=detail)

class PermissionDeniedError(VoiceNoteError):
    """Raised when user lacks permission for an action."""
    def __init__(self, message: str = "Permission denied", detail: Optional[Any] = None):
        super().__init__(message, code="PERMISSION_DENIED", status_code=403, detail=detail)

class NotFoundError(VoiceNoteError):
    """Raised when a resource is not found."""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            f"{resource} with id {identifier} not found", 
            code="NOT_FOUND", 
            status_code=404
        )

class ValidationError(VoiceNoteError):
    """Raised when request validation fails."""
    def __init__(self, message: str, detail: Optional[Any] = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400, detail=detail)

class AIServiceError(VoiceNoteError):
    """Raised when an external AI service fails."""
    def __init__(self, message: str, detail: Optional[Any] = None):
        super().__init__(message, code="AI_SERVICE_ERROR", status_code=502, detail=detail)

class RAGError(VoiceNoteError):
    """Raised when RAG retrieval or processing fails."""
    def __init__(self, message: str, detail: Optional[Any] = None):
        super().__init__(message, code="RAG_ERROR", status_code=500, detail=detail)
