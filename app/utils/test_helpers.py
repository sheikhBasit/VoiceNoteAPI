"""
Test Helper Utilities - Wraps validation functions for test compatibility

Maps test expectations to actual implementation.
"""

from app.utils.ai_service_utils import AIServiceError
from app.utils.users_validation import ValidationError

# Make AIServiceError available from users_validation for test compatibility
__all__ = [
    "validate_email",
    "validate_device_model",
    "validate_transcript",
    "validate_title",
    "validate_password",
    "ValidationError",
    "AIServiceError",
]


def validate_email(email: str):
    """Validate email - wraps users_validation."""
    from app.utils.users_validation import validate_email as _validate_email

    try:
        return _validate_email(email)
    except ValidationError as e:
        raise AIServiceError(str(e))


def validate_device_model(model: str):
    """Validate device model - wraps users_validation."""
    from app.utils.users_validation import (
        validate_device_model as _validate_device_model,
    )

    try:
        return _validate_device_model(model)
    except ValidationError as e:
        raise AIServiceError(str(e))


def validate_transcript(text: str):
    """Validate transcript - validates it's a string."""
    if not isinstance(text, str):
        raise AIServiceError("Transcript must be a string")
    if len(text) > 100000:
        raise AIServiceError("Transcript too long")
    if len(text) < 1:
        raise AIServiceError("Transcript cannot be empty")
    # Check for dangerous patterns - SQL injection
    dangerous_patterns = [
        "DROP TABLE",
        "DELETE FROM",
        "TRUNCATE",
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
    ]
    for pattern in dangerous_patterns:
        if pattern.upper() in text.upper():
            raise AIServiceError("Dangerous content detected in transcript")
    # Check for XSS patterns
    xss_patterns = ["<script", "<img", "javascript:", "onerror=", "onclick=", "onload="]
    for pattern in xss_patterns:
        if pattern in text.lower():
            raise AIServiceError("XSS detected in transcript")
    return text


def validate_title(title: str):
    """Validate title - validates it's a string."""
    if not isinstance(title, str):
        raise AIServiceError("Title must be a string")
    if len(title) > 255:
        raise AIServiceError("Title too long")
    if len(title) < 1:
        raise AIServiceError("Title cannot be empty")
    # Check for dangerous patterns
    if "<script>" in title.lower() or "<img" in title.lower():
        raise AIServiceError("Dangerous HTML detected in title")
    # Check for XSS patterns
    xss_patterns = ["<script", "javascript:", "onerror=", "onclick=", "onload="]
    for pattern in xss_patterns:
        if pattern in title.lower():
            raise AIServiceError("XSS detected in title")
    return title


def validate_password(password: str):
    """Validate password requirements."""
    if len(password) < 8:
        raise AIServiceError("Password too short (minimum 8 characters)")
    if len(password) > 256:
        raise AIServiceError("Password too long (maximum 256 characters)")
    return password


def validate_json_response(response: str):
    """Validate JSON response."""
    import json

    if not response or not response.strip():
        raise AIServiceError("Empty response")
    try:
        json.loads(response)
        return response
    except json.JSONDecodeError as e:
        raise AIServiceError(f"Invalid JSON: {str(e)}")
