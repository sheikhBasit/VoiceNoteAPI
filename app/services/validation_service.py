import re
from typing import List

# Constants
EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
DEVICE_MODEL_PATTERN = r"^[a-zA-Z0-9\s\-._()]+$"
MAX_JARGONS = 50
MAX_JARGON_LENGTH = 100
MAX_DEVICE_MODEL = 255
MAX_SYSTEM_PROMPT = 2000

class ValidationError(Exception):
    """Validation error for user data."""

class ValidationService:
    @staticmethod
    def validate_email(email: str) -> str:
        email = email.strip().lower()
        if not email or len(email) > 254:
            raise ValidationError("Invalid email address")
        if not re.match(EMAIL_PATTERN, email):
            raise ValidationError("Invalid email format")
        return email

    @staticmethod
    def validate_work_hours(start_hour: int, end_hour: int) -> tuple:
        if not isinstance(start_hour, int) or not isinstance(end_hour, int):
            raise ValidationError("Work hours must be integers")
        if start_hour < 0 or start_hour > 23 or end_hour < 0 or end_hour > 23:
            raise ValidationError("Work hours must be between 0 and 23")
        if start_hour > end_hour:
            raise ValidationError("work_start_hour must be <= work_end_hour")
        return start_hour, end_hour

    @staticmethod
    def validate_work_days(work_days: List[int]) -> List[int]:
        if not isinstance(work_days, list):
            raise ValidationError("work_days must be a list")
        for day in work_days:
            if not isinstance(day, int) or day < 0 or day > 6:
                raise ValidationError("work_days must be integers between 0-6")
        return list(dict.fromkeys(work_days))

    @staticmethod
    def validate_jargons(jargons: List[str]) -> List[str]:
        if not isinstance(jargons, list):
            raise ValidationError("jargons must be a list")
        if len(jargons) > MAX_JARGONS:
            raise ValidationError(f"Maximum {MAX_JARGONS} jargons allowed")
        
        cleaned = []
        seen = set()
        for jargon in jargons:
            if not isinstance(jargon, str):
                raise ValidationError("Each jargon must be a string")
            j = jargon.strip()
            if not j or len(j) > MAX_JARGON_LENGTH:
                raise ValidationError(f"Jargon must be 1-{MAX_JARGON_LENGTH} characters")
            if j.lower() not in seen:
                seen.add(j.lower())
                cleaned.append(j)
        return cleaned

    @staticmethod
    def validate_device_model(device_model: str) -> str:
        if not isinstance(device_model, str):
            raise ValidationError("device_model must be a string")
        dm = device_model.strip()
        if not dm or len(dm) > MAX_DEVICE_MODEL:
            raise ValidationError(f"device_model must be 1-{MAX_DEVICE_MODEL} characters")
        if not re.match(DEVICE_MODEL_PATTERN, dm):
            raise ValidationError("device_model contains invalid characters")
        return dm

    @staticmethod
    def validate_device_id(device_id: str) -> str:
        if not isinstance(device_id, str) or len(device_id.strip()) < 5:
            raise ValidationError("device_id must be at least 5 characters")
        return device_id.strip()

    @staticmethod
    def validate_system_prompt(prompt: str) -> str:
        if not isinstance(prompt, str):
            raise ValidationError("system_prompt must be a string")
        p = prompt.strip()
        if len(p) > MAX_SYSTEM_PROMPT:
            raise ValidationError(f"system_prompt must be <= {MAX_SYSTEM_PROMPT}")
        return p

    @staticmethod
    def validate_user_id(user_id: str) -> str:
        if not isinstance(user_id, str) or not re.match(r"^[a-zA-Z0-9_-]+$", user_id):
            raise ValidationError("user_id contains invalid characters")
        return user_id

    @staticmethod
    def validate_name(name: str) -> str:
        if not isinstance(name, str) or len(name.strip()) < 2:
            raise ValidationError("name must be at least 2 characters")
        return name.strip()[:255]
