import enum
import time
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    Float,
)
from sqlalchemy.dialects.postgresql import JSONB  # Specific for PostgreSQL performance
from sqlalchemy.orm import relationship

from .session import Base

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


class TaskStatus(enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


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


class SubscriptionTier(enum.Enum):
    FREE = "FREE"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    GUEST = "GUEST"
    ENTERPRISE = "ENTERPRISE"


# --- ASSOCIATION TABLES ---

folder_participants = Table(
    "folder_participants",
    Base.metadata,
    Column(
        "folder_id", String, ForeignKey("folders.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "user_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("role", String, default="MEMBER"),  # OWNER, EDITOR, VIEWER
    Column("joined_at", BigInteger, default=lambda: int(time.time() * 1000)),
)


team_members = Table(
    "team_members",
    Base.metadata,
    Column(
        "team_id", String, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "user_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("joined_at", BigInteger, default=lambda: int(time.time() * 1000)),
)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # UUID (not just device ID anymore)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    profile_picture_url = Column(String, nullable=True)  # New: Profile Picture

    # Auth & Device Management
    # Stores list of dicts: [{"device_id": "...", "device_model": "...", "biometric_token": "...", "authorized_at": 123}]
    authorized_devices = Column(JSONB, default=list)

    # Session Info
    current_device_id = Column(String, nullable=True)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.GUEST)
    plan_id = Column(String, ForeignKey("service_plans.id"), nullable=True)
    org_id = Column(
        String, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )

    # Usage Stats (JSONB cache for quick admin view)
    usage_stats = Column(
        JSONB,
        default=lambda: {
            "total_audio_minutes": 0.0,
            "total_notes": 0,
            "total_tasks": 0,
            "last_usage_at": None,
        },
    )

    password_hash = Column(String, nullable=True)  # For Admin Web Login
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
    jargons = Column(JSONB, default=list)  # Custom vocabulary for Whisper/Llama

    # Admin System (NEW)
    is_admin = Column(Boolean, default=False, index=True)
    admin_permissions = Column(JSON, default=dict)  # Flexible permission storage
    admin_created_at = Column(BigInteger, nullable=True)
    admin_last_action = Column(BigInteger, nullable=True)

    # App Settings
    show_floating_button = Column(Boolean, default=True)
    work_start_hour = Column(Integer, default=9)
    work_end_hour = Column(Integer, default=17)
    work_days = Column(JSONB, default=lambda: [2, 3, 4, 5, 6])  # 1=Mon...7=Sun
    timezone = Column(String, default="UTC", index=True)  # e.g. "America/New_York"
    preferred_languages = Column(
        JSONB, default=lambda: ["en"]
    )  # New: Multilingual support

    # Relationships with CASCADE deletion
    notes = relationship(
        "Note",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,  # Use database-level CASCADE
    )
    folders = relationship(
        "Folder",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    organization = relationship("Organization", back_populates="users", foreign_keys=[org_id])
    shared_folders = relationship(
        "Folder", secondary=folder_participants, back_populates="participants"
    )
    integrations = relationship(
        "UserIntegration",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    owned_teams = relationship("Team", back_populates="owner")
    teams = relationship("Team", secondary=team_members, back_populates="members")


class RefreshToken(Base):
    """
    Stores refresh tokens for secure session management.
    Allows for revocation and rotation.
    """
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=lambda: str(__import__("uuid").uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token = Column(String(255), unique=True, index=True)
    expires_at = Column(BigInteger, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))

    user = relationship("User", back_populates="refresh_tokens")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name = Column(String, nullable=False)
    color = Column(String, default="#FFFFFF")  # Hex color for UI
    icon = Column(String, default="folder")  # Icon name/emoji

    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))

    user = relationship("User", back_populates="folders")
    notes = relationship("Note", back_populates="folder")
    participants = relationship(
        "User", secondary=folder_participants, back_populates="shared_folders"
    )


class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))

    owner = relationship("User", back_populates="owned_teams")
    members = relationship("User", secondary=team_members, back_populates="teams")
    notes = relationship("Note", back_populates="team")
    tasks = relationship("Task", back_populates="team")


class Note(Base):
    __tablename__ = "notes"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    folder_id = Column(
        String, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    team_id = Column(
        String, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title = Column(String)
    summary = Column(Text)

    # Transcripts from different engines for comparison
    transcript_groq = Column(Text)
    transcript_deepgram = Column(Text)
    transcript_android = Column(Text)  # Fallback

    # Audio Storage
    audio_url = Column(String, nullable=True)  # Enhanced version
    raw_audio_url = Column(String, nullable=True)  # Original

    # Metadata & Status
    timestamp = Column(BigInteger, default=lambda: int(time.time() * 1000), index=True)
    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    priority = Column(Enum(Priority), default=Priority.MEDIUM, index=True)
    status = Column(Enum(NoteStatus), default=NoteStatus.PENDING, index=True)

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

    # External Data (Client-Side Storage)
    document_uris = Column(
        JSONB, default=lambda: []
    )  # Local device URIs (e.g., content://...)
    image_uris = Column(JSONB, default=lambda: [])  # Local device image URIs
    links = Column(JSONB, default=lambda: [])
    embedding = Column(Vector(384))  # Dimension for all-MiniLM-L6-v2 Embeddings
    embedding_version = Column(Integer, default=1)  # Cache versioning
    languages = Column(JSONB, default=lambda: [])  # New: Langs detected or hinted
    stt_model = Column(String, default="nova")  # New: nova, whisper, both
    tags = Column(JSONB, default=list)  # New: Dynamic AI-generated categories

    # AI Background Results (NEW)
    semantic_analysis = Column(JSONB, nullable=True)  # Result of background analysis
    ai_responses = Column(JSONB, default=lambda: [])  # History of Q&A task results
    processing_time_ms = Column(BigInteger, nullable=True)  # New: Time taken for AI analysis

    # Index for JSONB tags if we want to search by them effectively
    __table_args__ = (Index("ix_notes_tags", tags, postgresql_using="gin"),)

    # Relationships with CASCADE deletion
    user = relationship("User", back_populates="notes")
    folder = relationship("Folder", back_populates="notes")
    tasks = relationship(
        "Task",
        back_populates="note",
        cascade="all, delete-orphan",
        passive_deletes=True,  # Use database-level CASCADE
    )
    team = relationship("Team", back_populates="notes")

    @property
    def transcript(self):
        """Returns the best available transcript."""
        return (
            self.transcript_deepgram
            or self.transcript_groq
            or self.transcript_android
            or ""
        )


from sqlalchemy import Index

# High-performance HNSW index for vector search (Cosine similarity optimized)
Index(
    "idx_notes_embedding",
    Note.embedding,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    note_id = Column(
        String, ForeignKey("notes.id", ondelete="CASCADE"), index=True, nullable=True
    )
    team_id = Column(
        String, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title = Column(String)  # Brief title
    description = Column(Text)  # Detailed instructions
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO, index=True)
    is_done = Column(Boolean, default=False, index=True)
    deadline = Column(BigInteger, nullable=True, index=True)
    priority = Column(Enum(Priority), default=Priority.MEDIUM, index=True)

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

    # --- MULTI-MEDIA & LINKS (Client-Side Storage) ---
    image_uris = Column(
        JSONB, default=lambda: []
    )  # Local device image URIs (content://...)
    document_uris = Column(
        JSONB, default=lambda: []
    )  # Local device document URIs (content://...)
    external_links = Column(JSONB, default=lambda: [])  # External web URLs with titles

    # Action Logic
    communication_type = Column(Enum(CommunicationType), nullable=True)
    is_action_approved = Column(Boolean, default=False)

    # NEW: Smart action suggestions (Google search, email drafts, WhatsApp, AI prompts)
    suggested_actions = Column(JSONB, nullable=True, default=dict)
    # Structure: {
    #   "google_search": {"query": "...", "url": "https://google.com/search?q=..."},
    #   "email": {"to": "...", "subject": "...", "body": "...", "mailto_link": "..."},
    #   "whatsapp": {"phone": "...", "message": "...", "deeplink": "..."},
    #   "ai_prompt": {"model": "...", "prompt": "...", "chat_url": "..."}
    # }

    note = relationship("Note", back_populates="tasks")
    team = relationship("Team", back_populates="tasks")


class ApiKey(Base):
    """
    API Keys table for failover key rotation.
    Stores multiple keys per service with priority-based rotation.
    """

    __tablename__ = "api_keys"

    id = Column(
        String, primary_key=True, default=lambda: str(__import__("uuid").uuid4())
    )
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
        __import__("sqlalchemy").UniqueConstraint(
            "service_name", "priority", name="uq_service_priority"
        ),
    )


class SystemSettings(Base):
    """
    Global system settings manageable by admins.
    Controls AI behavior, UI defaults, and system-wide thresholds.
    """

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, default=1)  # Single row for global settings

    # LLM Settings
    llm_model = Column(String(100), default="llama-3.3-70b-versatile")
    llm_fast_model = Column(String(100), default="llama-3.1-8b-instant")
    temperature = Column(
        Integer, default=3
    )  # Stored as int (0-10) for easier UI, converted to float (0.0-1.0)
    max_tokens = Column(Integer, default=4096)
    top_p = Column(Integer, default=9)  # Stored as int (0-10)

    # STT Settings
    stt_engine = Column(String(50), default="deepgram")  # 'deepgram', 'groq'
    groq_whisper_model = Column(String(100), default="whisper-large-v3-turbo")
    deepgram_model = Column(String(50), default="nova-3")

    # Semantic Analysis Settings
    semantic_analysis_prompt = Column(Text, nullable=True)

    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    # Note: Foreign key to users.id for updated_by
    updated_by = Column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


# --- COMMERCIAL & BILLING MODELS ---


class ServicePlan(Base):
    """
    Defines billing tiers and limits.
    """

    __tablename__ = "service_plans"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # 'FREE', 'PRO', 'ENTERPRISE'

    # Pricing
    price_per_minute = Column(Integer, default=10)  # in credits
    monthly_credits = Column(Integer, default=100)

    # Features
    ai_models_allowed = Column(JSON, default=lambda: ["llama-3.1", "nova-2"])
    can_use_rag = Column(Boolean, default=True)
    max_storage_mb = Column(Integer, default=500)

    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))


class Wallet(Base):
    """
    Stores user credit balance for usage-based billing.
    One-to-One with User.
    """

    __tablename__ = "wallets"

    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    balance = Column(
        Integer, default=0
    )  # Stored in smallest currency unit (e.g., cents or credits) or tokens
    currency = Column(String(3), default="USD")
    is_frozen = Column(Boolean, default=False)  # If payment fails

    # Stripe Metadata
    stripe_customer_id = Column(String, index=True, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    auto_recharge_enabled = Column(Boolean, default=False)
    recharge_threshold = Column(Integer, default=500)  # e.g. $5.00
    recharge_amount = Column(Integer, default=2000)  # e.g. $20.00

    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))

    user = relationship("User", back_populates="wallet")


User.wallet = relationship(
    "Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan"
)
User.plan = relationship("ServicePlan", backref="users")


class Transaction(Base):
    """
    Ledger for all credit movements (Deposits, Usage, Refunds).
    Immutable history.
    """

    __tablename__ = "transactions"

    id = Column(
        String, primary_key=True, default=lambda: str(__import__("uuid").uuid4())
    )
    wallet_id = Column(
        String, ForeignKey("wallets.user_id", ondelete="CASCADE"), index=True
    )
    amount = Column(Integer, nullable=False)  # Negative for usage, Positive for deposit
    balance_after = Column(Integer, nullable=False)  # Snapshot of balance
    type = Column(String(20), nullable=False)  # 'DEPOSIT', 'USAGE', 'REFUND', 'BONUS'
    description = Column(
        String
    )  # e.g. "Transcription: 5 mins" or "Stripe Payment #123"
    reference_id = Column(String, nullable=True)  # ID of Note/Task/StripeCharge
    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))


class UsageLog(Base):
    """
    Granular log of API resource consumption.
    Used for metering and anomaly detection.
    """

    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint = Column(String, index=True)  # e.g. '/transcribe', '/rag/search'

    # Metrics
    duration_seconds = Column(Integer, default=0)  # Processing time or audio duration
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    provider = Column(String)  # 'groq', 'deepgram', 'tavily'
    model = Column(String)  # 'llama-3.1', 'nova-2'

    cost_estimated = Column(Integer, default=0)  # In credits/cents
    status = Column(Integer, default=200)  # HTTP Status
    timestamp = Column(BigInteger, default=lambda: int(time.time() * 1000))


class AdminActionLog(Base):
    """
    Persistent audit log for admin actions.
    Tracks all administrative operations for compliance and security.
    """

    __tablename__ = "admin_action_logs"

    id = Column(String, primary_key=True)  # UUID
    admin_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action = Column(
        String, nullable=False, index=True
    )  # e.g., "DELETE_USER", "UPDATE_PERMISSIONS"
    target_id = Column(String, nullable=True)  # ID of affected resource
    details = Column(JSONB, default=dict)  # Additional context
    ip_address = Column(String, nullable=True)  # Request IP
    user_agent = Column(Text, nullable=True)  # Request user agent
    timestamp = Column(
        BigInteger, default=lambda: int(time.time() * 1000), nullable=False, index=True
    )

    # Relationship
    admin = relationship("User", foreign_keys=[admin_id])


# --- B2B ORGANIZATIONAL MODELS ---


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True)
    name = Column(String, index=True, nullable=False)
    admin_user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"))
    corporate_wallet_id = Column(
        String, nullable=True
    )  # Link to a shared Wallet if needed
    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))

    users = relationship(
        "User", back_populates="organization", foreign_keys="[User.org_id]"
    )
    work_locations = relationship("WorkLocation", back_populates="organization")


class WorkLocation(Base):
    __tablename__ = "work_locations"

    id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    radius = Column(Integer, default=100)  # Radius in meters

    organization = relationship("Organization", back_populates="work_locations")


class UserIntegration(Base):
    """
    Stores OAuth tokens for third-party services (Google, Notion, Trello).
    Encrypted storage recommended in production.
    """

    __tablename__ = "user_integrations"

    id = Column(
        String, primary_key=True, default=lambda: str(__import__("uuid").uuid4())
    )
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider = Column(String, nullable=False, index=True)  # 'google', 'notion', 'trello'
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(BigInteger, nullable=True)  # Unix timestamp in ms
    scope = Column(String, nullable=True)
    meta_data = Column(JSONB, default=dict)  # Renamed from metadata to avoid SQL conflict

    created_at = Column(BigInteger, default=lambda: int(time.time() * 1000))
    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))

    user = relationship("User", back_populates="integrations")

