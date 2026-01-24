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
    PROCESSING = "PROCESSING"
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
    password_hash = Column(String, nullable=True) # For Admin Web Login
    last_login = Column(BigInteger, default=lambda: int(time.time() * 1000))
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(BigInteger, nullable=True)
    deleted_by = Column(String, nullable=True)
    deletion_reason = Column(String, nullable=True)
    can_restore = Column(Boolean, default=True)
    
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

    # Relationships with CASCADE deletion
    notes = relationship(
        "Note", 
        back_populates="user", 
        cascade="all, delete-orphan",
        passive_deletes=True  # Use database-level CASCADE
    )


class Note(Base):
    __tablename__ = "notes"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
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
    
    # Deletion Metadata (Enhanced)
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(BigInteger, nullable=True)
    deleted_by = Column(String, nullable=True)  # User ID who performed deletion
    deletion_reason = Column(Text, nullable=True)  # Reason for deletion
    can_restore = Column(Boolean, default=True)  # Whether item can be restored
    is_pinned = Column(Boolean, default=False)
    is_liked = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_encrypted = Column(Boolean, default=False)
    
    # External Data
    document_urls = Column(JSON, default=list)
    links = Column(JSON, default=list)
    embedding = Column(Vector(384)) # Dimension for all-MiniLM-L6-v2 Embeddings
    embedding_version = Column(Integer, default=1) # Cache versioning
    
    # AI Background Results (NEW)
    semantic_analysis = Column(JSONB, nullable=True) # Result of background analysis
    ai_responses = Column(JSONB, default=list)      # History of Q&A task results
    
    # Relationships with CASCADE deletion
    user = relationship("User", back_populates="notes")
    tasks = relationship(
        "Task", 
        back_populates="note", 
        cascade="all, delete-orphan",
        passive_deletes=True  # Use database-level CASCADE
    )

    @property
    def transcript(self):
        """Returns the best available transcript."""
        return self.transcript_deepgram or self.transcript_groq or self.transcript_android or ""

from sqlalchemy import Index
# High-performance HNSW index for vector search (Cosine similarity optimized)
Index('idx_notes_embedding', Note.embedding, postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64})


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    note_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"), index=True)
    description = Column(Text)
    is_done = Column(Boolean, default=False)
    deadline = Column(BigInteger, nullable=True)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    
    # Deletion Metadata (Enhanced)
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(BigInteger, nullable=True)
    deleted_by = Column(String, nullable=True)  # User ID who performed deletion
    deletion_reason = Column(Text, nullable=True)  # Reason for deletion
    can_restore = Column(Boolean, default=True)  # Whether item can be restored
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

class SystemSettings(Base):
    """
    Global system settings manageable by admins.
    Controls AI behavior, UI defaults, and system-wide thresholds.
    """
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, default=1) # Single row for global settings
    
    # LLM Settings
    llm_model = Column(String(100), default="llama-3.3-70b-versatile")
    llm_fast_model = Column(String(100), default="llama-3.1-8b-instant")
    temperature = Column(Integer, default=3) # Stored as int (0-10) for easier UI, converted to float (0.0-1.0)
    max_tokens = Column(Integer, default=4096)
    top_p = Column(Integer, default=9) # Stored as int (0-10)
    
    # STT Settings
    stt_engine = Column(String(50), default="deepgram") # 'deepgram', 'groq'
    groq_whisper_model = Column(String(100), default="whisper-large-v3-turbo")
    deepgram_model = Column(String(50), default="nova-3")
    
    # Semantic Analysis Settings
    semantic_analysis_prompt = Column(Text, nullable=True)
    
    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    # Note: Foreign key to users.id for updated_by
    updated_by = Column(String, ForeignKey("users.id")) 

# --- COMMERCIAL & BILLING MODELS (NEW) ---

class Wallet(Base):
    """
    Stores user credit balance for usage-based billing.
    One-to-One with User.
    """
    __tablename__ = "wallets"
    
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    balance = Column(Integer, default=0) # Stored in smallest currency unit (e.g., cents or credits) or tokens
    currency = Column(String(3), default="USD")
    is_frozen = Column(Boolean, default=False) # If payment fails
    
    # Stripe Metadata
    stripe_customer_id = Column(String, index=True, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    auto_recharge_enabled = Column(Boolean, default=False)
    recharge_threshold = Column(Integer, default=500) # e.g. $5.00
    recharge_amount = Column(Integer, default=2000)   # e.g. $20.00
    
    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    
    user = relationship("User", backref="wallet")

class Transaction(Base):
    """
    Ledger for all credit movements (Deposits, Usage, Refunds).
    Immutable history.
    """
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    wallet_id = Column(String, ForeignKey("wallets.user_id"), index=True)
    amount = Column(Integer, nullable=False) # Negative for usage, Positive for deposit
    balance_after = Column(Integer, nullable=False) # Snapshot of balance
    type = Column(String(20), nullable=False) # 'DEPOSIT', 'USAGE', 'REFUND', 'BONUS'
    description = Column(String) # e.g. "Transcription: 5 mins" or "Stripe Payment #123"
    reference_id = Column(String, nullable=True) # ID of Note/Task/StripeCharge
    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))

class UsageLog(Base):
    """
    Granular log of API resource consumption.
    Used for metering and anomaly detection.
    """
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    endpoint = Column(String, index=True) # e.g. '/transcribe', '/rag/search'
    
    # Metrics
    duration_seconds = Column(Integer, default=0) # Processing time or audio duration
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    provider = Column(String) # 'groq', 'deepgram', 'tavily'
    model = Column(String)    # 'llama-3.1', 'nova-2'
    
    cost_estimated = Column(Integer, default=0) # In credits/cents
    status = Column(Integer, default=200) # HTTP Status
    timestamp = Column(BigInteger, default=lambda: int(time.time() * 1000)) 
    