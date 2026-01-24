from pydantic import BaseModel, ConfigDict, Field, EmailStr, HttpUrl
from typing import List, Optional
from enum import Enum

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

class ContactEntity(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None # Validates email format automatically

class LinkEntity(BaseModel):
    title: str
    url: HttpUrl # Validates proper URL format

class TaskBase(BaseModel):
    description: str = Field(..., min_length=1)
    priority: Priority = Priority.MEDIUM
    deadline: Optional[int] = None
    
    # Use default_factory to avoid mutable default issues
    assigned_entities: List[ContactEntity] = Field(default_factory=list)
    image_urls: List[HttpUrl] = Field(default_factory=list)
    document_urls: List[HttpUrl] = Field(default_factory=list)
    external_links: List[LinkEntity] = Field(default_factory=list)
    
    communication_type: Optional[CommunicationType] = None
    is_action_approved: bool = False

class TaskCreate(TaskBase):
    note_id: str

class TaskUpdate(BaseModel):
    description: Optional[str] = None
    priority: Optional[Priority] = None
    deadline: Optional[int] = None
    is_done: Optional[bool] = None
    assigned_entities: Optional[List[ContactEntity]] = None
    image_urls: Optional[List[HttpUrl]] = None
    document_urls: Optional[List[HttpUrl]] = None
    external_links: Optional[List[LinkEntity]] = None
    communication_type: Optional[CommunicationType] = None
    is_action_approved: bool = False
    is_deleted: Optional[bool] = None

class TaskResponse(TaskBase):
    id: str
    note_id: str
    is_done: bool
    is_deleted: bool
    created_at: int
    updated_at: Optional[int] = None
    deleted_at: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)