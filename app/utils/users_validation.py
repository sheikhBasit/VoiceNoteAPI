"""
Phase 2 - Users API Validation & Security Utilities

Provides validation, sanitization, and security helpers for Users API.
"""

from typing import List, Optional
from datetime import datetime
import re
from pydantic import EmailStr, validator, BaseModel, Field

# Email regex pattern (RFC 5322 simplified)
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Device model allowed characters
DEVICE_MODEL_PATTERN = r'^[a-zA-Z0-9\s\-._()]+$'

# Max lengths
MAX_JARGONS = 50
MAX_JARGON_LENGTH = 100
MAX_DEVICE_MODEL = 255
MAX_SYSTEM_PROMPT = 2000


class ValidationError(Exception):
    """Validation error for user data."""
    pass


def validate_email(email: str) -> str:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email (lowercase)
        
    Raises:
        ValidationError: If email is invalid
    """
    email = email.strip().lower()
    
    if not email or len(email) > 254:
        raise ValidationError("Invalid email address")
    
    if not re.match(EMAIL_PATTERN, email):
        raise ValidationError("Invalid email format")
    
    return email


def validate_work_hours(start_hour: int, end_hour: int) -> tuple:
    """
    Validate work hours (must be 0-23).
    
    Args:
        start_hour: Work start hour (0-23)
        end_hour: Work end hour (0-23)
        
    Returns:
        Tuple of (start_hour, end_hour)
        
    Raises:
        ValidationError: If hours are invalid
    """
    if not isinstance(start_hour, int) or not isinstance(end_hour, int):
        raise ValidationError("Work hours must be integers")
    
    if start_hour < 0 or start_hour > 23:
        raise ValidationError("work_start_hour must be between 0 and 23")
    
    if end_hour < 0 or end_hour > 23:
        raise ValidationError("work_end_hour must be between 0 and 23")
    
    if start_hour > end_hour:
        raise ValidationError("work_start_hour must be <= work_end_hour")
    
    return start_hour, end_hour


def validate_work_days(work_days: List[int]) -> List[int]:
    """
    Validate work days (0=Monday, 6=Sunday).
    
    Args:
        work_days: List of work day numbers (0-6)
        
    Returns:
        Validated work days
        
    Raises:
        ValidationError: If days are invalid
    """
    if not isinstance(work_days, list):
        raise ValidationError("work_days must be a list")
    
    if len(work_days) == 0 or len(work_days) > 7:
        raise ValidationError("work_days must have 1-7 days")
    
    for day in work_days:
        if not isinstance(day, int) or day < 0 or day > 6:
            raise ValidationError("work_days must be integers between 0-6")
    
    # Remove duplicates, keep order
    seen = set()
    unique_days = []
    for day in work_days:
        if day not in seen:
            seen.add(day)
            unique_days.append(day)
    
    return unique_days


def validate_jargons(jargons: List[str]) -> List[str]:
    """
    Validate jargons list.
    
    Args:
        jargons: List of jargon strings
        
    Returns:
        Validated and deduplicated jargons
        
    Raises:
        ValidationError: If jargons are invalid
    """
    if not isinstance(jargons, list):
        raise ValidationError("jargons must be a list")
    
    if len(jargons) > MAX_JARGONS:
        raise ValidationError(f"Maximum {MAX_JARGONS} jargons allowed")
    
    cleaned = []
    seen = set()
    
    for jargon in jargons:
        if not isinstance(jargon, str):
            raise ValidationError("Each jargon must be a string")
        
        jargon = jargon.strip()
        
        if len(jargon) == 0 or len(jargon) > MAX_JARGON_LENGTH:
            raise ValidationError(f"Jargon must be 1-{MAX_JARGON_LENGTH} characters")
        
        # Normalize to lowercase for deduplication
        jargon_lower = jargon.lower()
        if jargon_lower not in seen:
            seen.add(jargon_lower)
            cleaned.append(jargon)
    
    return cleaned


def validate_device_model(device_model: str) -> str:
    """
    Validate and sanitize device model string.
    
    Args:
        device_model: Device model string
        
    Returns:
        Validated device model
        
    Raises:
        ValidationError: If device model is invalid
    """
    if not isinstance(device_model, str):
        raise ValidationError("device_model must be a string")
    
    device_model = device_model.strip()
    
    if len(device_model) == 0 or len(device_model) > MAX_DEVICE_MODEL:
        raise ValidationError(f"device_model must be 1-{MAX_DEVICE_MODEL} characters")
    
    # Only allow alphanumeric, spaces, hyphens, periods, underscores, parentheses
    if not re.match(DEVICE_MODEL_PATTERN, device_model):
        raise ValidationError("device_model contains invalid characters")
    
    return device_model


def validate_system_prompt(system_prompt: str) -> str:
    """
    Validate system prompt string.
    
    Args:
        system_prompt: System prompt string
        
    Returns:
        Validated system prompt
        
    Raises:
        ValidationError: If system prompt is invalid
    """
    if not isinstance(system_prompt, str):
        raise ValidationError("system_prompt must be a string")
    
    system_prompt = system_prompt.strip()
    
    if len(system_prompt) > MAX_SYSTEM_PROMPT:
        raise ValidationError(f"system_prompt must be <= {MAX_SYSTEM_PROMPT} characters")
    
    return system_prompt


def sanitize_string(value: str, max_length: int = 500) -> str:
    """
    Sanitize string input (remove dangerous characters).
    
    Args:
        value: String to sanitize
        max_length: Maximum length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""
    
    # Strip whitespace
    value = value.strip()
    
    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
    
    # Remove null bytes (SQL injection risk)
    value = value.replace('\0', '')
    
    # Remove control characters except newline/tab
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\t')
    
    return value


def validate_name(name: str) -> str:
    """
    Validate user name.
    
    Args:
        name: User name
        
    Returns:
        Validated name
        
    Raises:
        ValidationError: If name is invalid
    """
    if not isinstance(name, str):
        raise ValidationError("name must be a string")
    
    name = sanitize_string(name, max_length=255)
    
    if len(name) < 2 or len(name) > 255:
        raise ValidationError("name must be 2-255 characters")
    
    return name


def validate_user_id(user_id: str) -> str:
    """
    Validate user ID format.
    
    Args:
        user_id: User ID
        
    Returns:
        Validated user ID
        
    Raises:
        ValidationError: If user ID is invalid
    """
    if not isinstance(user_id, str):
        raise ValidationError("user_id must be a string")
    
    user_id = user_id.strip()
    
    if len(user_id) == 0 or len(user_id) > 100:
        raise ValidationError("user_id must be 1-100 characters")
    
    # Allow alphanumeric, hyphens, underscores only
    if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
        raise ValidationError("user_id contains invalid characters")
    
    return user_id


def validate_token(token: str) -> str:
    """
    Validate authentication token.
    
    Args:
        token: Authentication token
        
    Returns:
        Validated token
        
    Raises:
        ValidationError: If token is invalid
    """
    if not isinstance(token, str):
        raise ValidationError("token must be a string")
    
    token = token.strip()
    
    if len(token) < 10 or len(token) > 1000:
        raise ValidationError("token must be 10-1000 characters")
    
    return token


def validate_device_id(device_id: str) -> str:
    """
    Validate device ID.
    
    Args:
        device_id: Device ID
        
    Returns:
        Validated device ID
        
    Raises:
        ValidationError: If device ID is invalid
    """
    if not isinstance(device_id, str):
        raise ValidationError("device_id must be a string")
    
    device_id = device_id.strip()
    
    if len(device_id) < 5 or len(device_id) > 500:
        raise ValidationError("device_id must be 5-500 characters")
    
    return device_id


# Test the validators
if __name__ == "__main__":
    # Test email validation
    try:
        print("✅ Email validation:", validate_email("  user@example.com  "))
    except ValidationError as e:
        print("❌ Email validation error:", e)
    
    # Test work hours
    try:
        print("✅ Work hours validation:", validate_work_hours(9, 17))
    except ValidationError as e:
        print("❌ Work hours error:", e)
    
    # Test jargons
    try:
        print("✅ Jargons validation:", validate_jargons(["Python", "API", "python"]))
    except ValidationError as e:
        print("❌ Jargons error:", e)
    
    # Test device model
    try:
        print("✅ Device model validation:", validate_device_model("Samsung Galaxy S23"))
    except ValidationError as e:
        print("❌ Device model error:", e)
    
    print("\n✨ All validation functions working!")
