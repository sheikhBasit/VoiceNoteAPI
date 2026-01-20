from sqlalchemy import Column, String, BigInteger, Boolean, ForeignKey, Enum, Text, JSON, Integer
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .session import Base
import enum
import time

class Priority(enum.Enum):
    HIGH = "HIGH"; MEDIUM = "MEDIUM"; LOW = "LOW"

class NoteStatus(enum.Enum):
    PENDING = "PENDING"; DONE = "DONE"; DELAYED = "DELAYED"

class CommunicationType(enum.Enum):
    WHATSAPP = "WHATSAPP"; SMS = "SMS"; CALL = "CALL"; MEET = "MEET"; SLACK = "SLACK"

class UserRole(enum.Enum):
    STUDENT = "STUDENT"; TEACHER = "TEACHER"; DEVELOPER = "DEVELOPER"
    OFFICE_WORKER = "OFFICE_WORKER"; BUSINESS_MAN = "BUSINESS_MAN"
    PSYCHIATRIST = "PSYCHIATRIST"; PSYCHOLOGIST = "PSYCHOLOGIST"
    GENERIC = "GENERIC"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    token = Column(String)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    device_id = Column(String)
    device_model = Column(String)
    last_login = Column(BigInteger, default=lambda: int(time.time() * 1000))
    primary_role = Column(Enum(UserRole), default=UserRole.GENERIC)
    secondary_role = Column(Enum(UserRole), nullable=True)
    custom_role_description = Column(Text)
    system_prompt = Column(Text)
    jargons = Column(JSON, default=list) # Custom vocabulary
    show_floating_button = Column(Boolean, default=True)
    work_start_hour = Column(Integer, default=9)
    work_end_hour = Column(Integer, default=17)
    work_days = Column(JSON, default=lambda: [2,3,4,5,6])

class Note(Base):
    __tablename__ = "notes"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    title = Column(String)
    summary = Column(Text)
    transcript = Column(Text)
    transcript_groq = Column(Text)
    transcript_deepgram = Column(Text)
    transcript_elevenlabs = Column(Text)
    transcript_android = Column(Text)
    audio_url = Column(String, nullable=True)
    raw_audio_url = Column(String, nullable=True)
    timestamp = Column(BigInteger, default=lambda: int(time.time() * 1000))
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    status = Column(Enum(NoteStatus), default=NoteStatus.PENDING)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(BigInteger, nullable=True)
    is_pinned = Column(Boolean, default=False)
    is_liked = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_encrypted = Column(Boolean, default=False)
    document_urls = Column(JSON, default=list)
    links = Column(JSON, default=list) # List of title, url, type
    comparison_notes = Column(Text)
    embedding = Column(Vector(1536)) # For Semantic Search
    
    tasks = relationship("Task", back_populates="note", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    note_id = Column(String, ForeignKey("notes.id"))
    description = Column(Text)
    is_done = Column(Boolean, default=False)
    deadline = Column(BigInteger, nullable=True)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    google_prompt = Column(Text)
    ai_prompt = Column(Text)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    assigned_contact_name = Column(String, nullable=True)
    assigned_contact_phone = Column(String, nullable=True)
    communication_type = Column(Enum(CommunicationType), nullable=True)
    communication_scheduled_time = Column(BigInteger, nullable=True)
    custom_url = Column(String, nullable=True)
    is_action_approved = Column(Boolean, default=False)
    image_url = Column(String, nullable=True)
    document_urls = Column(JSON, default=list)

    note = relationship("Note", back_populates="tasks")