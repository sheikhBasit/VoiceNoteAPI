from sqlalchemy import Column, String, BigInteger, Boolean, ForeignKey, Enum, Text, JSON, Integer
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .session import Base
import enum
from sqlalchemy.dialects.postgresql import JSONB  # Specific for PostgreSQL performance
import time

# --- Enums ---

class Priority(enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class NoteStatus(enum.Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    DELAYED = "DELAYED"

class CommunicationType(enum.Enum):
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    CALL = "CALL"
    MEET = "MEET"
    SLACK = "SLACK"

class UserRole(enum.Enum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    DEVELOPER = "DEVELOPER"
    OFFICE_WORKER = "OFFICE_WORKER"
    BUSINESS_MAN = "BUSINESS_MAN"
    PSYCHIATRIST = "PSYCHIATRIST"
    PSYCHOLOGIST = "PSYCHOLOGIST"
    GENERIC = "GENERIC"

# --- Models ---

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True) # Usually Firebase UID or Device ID
    token = Column(String)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    device_id = Column(String)
    device_model = Column(String)
    last_login = Column(BigInteger, default=lambda: int(time.time() * 1000))
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(BigInteger, nullable=True)
    
    # AI Context & Roles
    primary_role = Column(Enum(UserRole), default=UserRole.GENERIC)
    secondary_role = Column(Enum(UserRole), nullable=True)
    custom_role_description = Column(Text)
    system_prompt = Column(Text)
    jargons = Column(JSON, default=list) # Custom vocabulary for Whisper/Llama
    
    # Admin System (NEW)
    is_admin = Column(Boolean, default=False, index=True)
    admin_permissions = Column(JSON, default=dict)  # Flexible permission storage
    admin_created_at = Column(BigInteger, nullable=True)
    admin_last_action = Column(BigInteger, nullable=True)
    
    # App Settings
    show_floating_button = Column(Boolean, default=True)
    work_start_hour = Column(Integer, default=9)
    work_end_hour = Column(Integer, default=17)
    work_days = Column(JSON, default=lambda: [2,3,4,5,6]) # 1=Mon...7=Sun

    # Relationships
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    title = Column(String)
    summary = Column(Text)
    
    # Transcripts from different engines for comparison
    transcript_groq = Column(Text)
    transcript_deepgram = Column(Text)
    transcript_android = Column(Text) # Fallback
    
    # Audio Storage
    audio_url = Column(String, nullable=True)     # Enhanced version
    raw_audio_url = Column(String, nullable=True) # Original
    
    # Metadata & Status
    timestamp = Column(BigInteger, default=lambda: int(time.time() * 1000))
    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    status = Column(Enum(NoteStatus), default=NoteStatus.PENDING)
    
    # Flags
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(BigInteger, nullable=True)
    is_pinned = Column(Boolean, default=False)
    is_liked = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_encrypted = Column(Boolean, default=False)
    
    # External Data
    document_urls = Column(JSON, default=list)
    links = Column(JSON, default=list)
    embedding = Column(Vector(1536)) # Dimension for Llama/OpenAI Embeddings
    
    # Relationships
    user = relationship("User", back_populates="notes")
    tasks = relationship("Task", back_populates="note", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    note_id = Column(String, ForeignKey("notes.id"), index=True)
    description = Column(Text)
    is_done = Column(Boolean, default=False)
    deadline = Column(BigInteger, nullable=True)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    
    # Deletion Metadata
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    
    # Notification tracking
    notified_at = Column(BigInteger, nullable=True)
    reminder_count = Column(Integer, default=0)
    notification_enabled = Column(Boolean, default=True)
    
    # --- FLEXIBLE ASSIGNMENT LOGIC ---
    # Stores: [{"name": "John", "phone": "123", "email": "j@test.com"}]
    assigned_entities = Column(JSONB, default=list) 
    
    # --- MULTI-MEDIA & LINKS ---
    image_urls = Column(JSONB, default=list)    # Multiple screenshots/photos
    document_urls = Column(JSONB, default=list) # Multiple PDFs/Docs
    external_links = Column(JSONB, default=list) # Multiple URLs with titles
    
    # Action Logic
    communication_type = Column(Enum(CommunicationType), nullable=True)
    is_action_approved = Column(Boolean, default=False)

    note = relationship("Note", back_populates="tasks")


class ApiKey(Base):
    """
    API Keys table for failover key rotation.
    Stores multiple keys per service with priority-based rotation.
    """
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    service_name = Column(String(50), nullable=False)  # 'deepgram', 'groq', 'openai'
    api_key = Column(Text, nullable=False)
    priority = Column(Integer, default=1)  # Lower = higher priority
    is_active = Column(Boolean, default=True)
    rate_limit_remaining = Column(Integer, default=1000)
    rate_limit_reset_at = Column(BigInteger, nullable=True)
    last_used_at = Column(BigInteger, nullable=True)
    last_error_at = Column(BigInteger, nullable=True)
    error_count = Column(Integer, default=0)
    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    notes = Column(Text, nullable=True)
    
    __table_args__ = (
        # Unique constraint on service_name + priority
        __import__('sqlalchemy').UniqueConstraint('service_name', 'priority', name='uq_service_priority'),
    )

    