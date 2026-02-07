from enum import Enum

from pydantic import BaseModel


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NoteStatus(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    DELAYED = "DELAYED"


class CommunicationType(str, Enum):
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    CALL = "CALL"
    MEET = "MEET"
    SLACK = "SLACK"


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    OFFICE_WORKER = "OFFICE_WORKER"
    DEVELOPER = "DEVELOPER"
    PSYCHIATRIST = "PSYCHIATRIST"
    PSYCHOLOGIST = "PSYCHOLOGIST"
    BUSINESS_MAN = "BUSINESS_MAN"
    OTHER = "OTHER"
    GENERIC = "GENERIC"


class ExternalLink(BaseModel):
    title: str = ""
    url: str = ""
    type: str = "web"
