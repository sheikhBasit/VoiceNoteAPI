from enum import Enum
from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CommunicationType(str, Enum):
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    CALL = "CALL"
    MEET = "MEET"
    SLACK = "SLACK"


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


class ContactEntity(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None  # Validates email format automatically


class LinkEntity(BaseModel):
    title: str
    url: HttpUrl  # Validates proper URL format


class TaskBase(BaseModel):
    title: Optional[str] = Field(None, description="Brief punchy title")
    description: str = Field(..., min_length=1)
    priority: Priority = Priority.MEDIUM
    deadline: Optional[int] = None

    # Use default_factory to avoid mutable default issues
    assigned_entities: List[ContactEntity] = Field(default_factory=list)
    image_uris: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("image_uris", "image_urls"),
    )  # Client-side URIs
    document_uris: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("document_uris", "document_urls"),
    )  # Client-side URIs
    external_links: List[LinkEntity] = Field(default_factory=list)

    communication_type: Optional[CommunicationType] = None
    is_action_approved: bool = False


class TaskCreate(TaskBase):
    note_id: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Priority] = None
    deadline: Optional[int] = None
    is_done: Optional[bool] = None
    assigned_entities: Optional[List[ContactEntity]] = None
    image_uris: Optional[List[str]] = None  # Client-side URIs
    document_uris: Optional[List[str]] = None  # Client-side URIs
    external_links: Optional[List[LinkEntity]] = None
    communication_type: Optional[CommunicationType] = None
    is_action_approved: bool = False
    is_deleted: Optional[bool] = None


class SuggestedActions(BaseModel):
    """Smart action suggestions for tasks."""

    google_search: Optional[dict] = None  # {"query": "...", "url": "..."}
    map: Optional[dict] = None  # {"location": "...", "url": "..."}
    email: Optional[dict] = (
        None  # {"to": "...", "subject": "...", "body": "...", "mailto_link": "..."}
    )
    whatsapp: Optional[dict] = (
        None  # {"phone": "...", "message": "...", "deeplink": "..."}
    )
    ai_prompt: Optional[dict] = (
        None  # {"model": "...", "prompt": "...", "chat_url": "..."}
    )


class TaskResponse(TaskBase):
    id: str
    note_id: Optional[str] = None
    is_done: bool
    status: TaskStatus
    is_deleted: bool
    created_at: int
    updated_at: Optional[int] = None
    deleted_at: Optional[int] = None
    suggested_actions: Optional[SuggestedActions] = None  # NEW: Smart actions
    model_config = ConfigDict(from_attributes=True)


class TaskStatistics(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    by_priority: dict
    by_status: dict
    completion_rate: float
