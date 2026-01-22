# VoiceNote Database Architecture & Setup

## Database Overview

**Type:** PostgreSQL 15+ with AsyncPG driver  
**Async Support:** Yes (SQLAlchemy AsyncIO)  
**Vector Support:** pgvector for embeddings  
**ORM:** SQLAlchemy 2.0+  

## Production Database

### Connection String
```
postgresql+asyncpg://user:password@host:port/database
```

### Environment Variable
```bash
DATABASE_URL="postgresql+asyncpg://postgres:password@db:5432/voicenote"
```

### Configuration (app/db/session.py)
```python
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@db:5432/voicenote")
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

## Testing Database

### Purpose
Isolated test database that runs in parallel with production, ensuring:
- Tests don't affect production data
- Clean state for each test session
- Fast rollback after each test
- Support for concurrent test execution

### Connection String
```
postgresql+asyncpg://postgres:password@localhost:5432/voicenote_test
```

### Configuration (tests/conftest.py)
```python
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/voicenote_test"
engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

### Features
- **Auto Schema Creation:** Pytest creates fresh schema for test session
- **Auto Rollback:** Each test transaction rolls back automatically
- **Isolated Sessions:** db_session fixture provides clean session per test
- **Standalone Tests:** Advanced performance/security tests skip DB init

## Database Schema

### Core Tables

#### 1. Users Table
```sql
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    token VARCHAR,
    name VARCHAR,
    email VARCHAR UNIQUE NOT NULL,
    device_id VARCHAR,
    device_model VARCHAR,
    last_login BIGINT,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at BIGINT,
    
    -- Roles & AI Context
    primary_role ENUM(user_role),
    secondary_role ENUM(user_role),
    is_admin BOOLEAN DEFAULT false,
    admin_permissions JSON,
    
    custom_role_description TEXT,
    system_prompt TEXT,
    jargons JSON DEFAULT [],
    
    -- Settings
    show_floating_button BOOLEAN DEFAULT true,
    work_start_hour INTEGER DEFAULT 9,
    work_end_hour INTEGER DEFAULT 17,
    work_days JSON DEFAULT [2,3,4,5,6],
    
    created_at BIGINT,
    updated_at BIGINT
);

-- Indexes
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_is_admin ON users(is_admin) WHERE is_admin = true;
```

#### 2. Notes Table
```sql
CREATE TABLE notes (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    title VARCHAR,
    summary TEXT,
    
    -- Transcripts (Multi-engine)
    transcript_groq TEXT,
    transcript_deepgram TEXT,
    transcript_android TEXT,
    
    -- Audio Storage
    audio_url VARCHAR,
    raw_audio_url VARCHAR,
    
    -- Metadata
    timestamp BIGINT,
    updated_at BIGINT,
    priority ENUM(priority),
    status ENUM(note_status),
    
    -- Flags
    is_deleted BOOLEAN DEFAULT false,
    deleted_at BIGINT,
    is_pinned BOOLEAN DEFAULT false,
    is_liked BOOLEAN DEFAULT false,
    is_archived BOOLEAN DEFAULT false,
    is_encrypted BOOLEAN DEFAULT false,
    
    -- External Data
    document_urls JSON DEFAULT [],
    links JSON DEFAULT [],
    embedding vector(1536)
);

-- Indexes
CREATE INDEX idx_user_id ON notes(user_id);
CREATE INDEX idx_timestamp ON notes(timestamp);
CREATE INDEX idx_status ON notes(status);
```

#### 3. Tasks Table
```sql
CREATE TABLE tasks (
    id VARCHAR PRIMARY KEY,
    note_id VARCHAR NOT NULL REFERENCES notes(id),
    description TEXT,
    is_done BOOLEAN DEFAULT false,
    deadline BIGINT,
    priority ENUM(priority),
    
    is_deleted BOOLEAN DEFAULT false,
    deleted_at BIGINT,
    created_at BIGINT,
    updated_at BIGINT,
    
    -- Notification
    notified_at BIGINT,
    reminder_count INTEGER DEFAULT 0,
    notification_enabled BOOLEAN DEFAULT true,
    
    -- Assignment (Flexible)
    assigned_entities JSONB DEFAULT [],
    
    -- Media
    image_urls JSONB DEFAULT [],
    document_urls JSONB DEFAULT [],
    external_links JSONB DEFAULT [],
    
    -- Communication
    communication_type ENUM(communication_type),
    is_action_approved BOOLEAN DEFAULT false
);

-- Indexes
CREATE INDEX idx_note_id ON tasks(note_id);
CREATE INDEX idx_deadline ON tasks(deadline);
CREATE INDEX idx_is_done ON tasks(is_done);
```

### Enums

#### UserRole
- STUDENT
- TEACHER
- DEVELOPER
- OFFICE_WORKER
- BUSINESS_MAN
- PSYCHIATRIST
- PSYCHOLOGIST
- GENERIC
- **ADMIN** (NEW)

#### Priority
- HIGH
- MEDIUM
- LOW

#### NoteStatus
- PENDING
- DONE
- DELAYED

#### CommunicationType
- WHATSAPP
- SMS
- CALL
- MEET
- SLACK

## Admin Role System

### New Admin Columns

```python
class User(Base):
    __tablename__ = "users"
    
    # ... existing columns ...
    
    # Admin System (NEW)
    is_admin = Column(Boolean, default=False, index=True)
    admin_permissions = Column(JSON, default=dict)  # Flexible permission storage
    admin_created_at = Column(BigInteger, nullable=True)
    admin_last_action = Column(BigInteger, nullable=True)
```

### Admin Permissions Structure

```json
{
    "can_view_all_users": true,
    "can_delete_users": true,
    "can_view_all_notes": true,
    "can_delete_notes": true,
    "can_manage_admins": true,
    "can_view_analytics": true,
    "can_modify_system_settings": true,
    "can_moderate_content": true,
    "can_manage_roles": true,
    "can_export_data": true,
    "created_at": 1705881600000,
    "granted_by": "admin_id"
}
```

## Seeding Database

### Development Seeding Script

```python
# scripts/seed_dev_db.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.models import User, Note, Task, UserRole, Priority, NoteStatus
from app.db.session import Base
import time
import uuid

async def seed_database():
    """Populate development database with sample data"""
    
    engine = create_async_engine("postgresql+asyncpg://postgres:password@db:5432/voicenote")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        # Create Admin User
        admin = User(
            id="admin_001",
            name="Admin User",
            email="admin@voicenote.com",
            token="admin_token_123",
            device_id="admin_device",
            device_model="Admin",
            is_admin=True,
            admin_permissions={
                "can_view_all_users": True,
                "can_delete_users": True,
                "can_view_all_notes": True,
                "can_delete_notes": True,
                "can_manage_admins": True,
                "can_view_analytics": True,
                "can_modify_system_settings": True,
                "can_moderate_content": True,
                "can_manage_roles": True,
                "can_export_data": True,
                "created_at": int(time.time() * 1000),
                "granted_by": "system"
            },
            primary_role=UserRole.DEVELOPER,
            last_login=int(time.time() * 1000)
        )
        
        # Create Regular Users
        regular_user = User(
            id="user_001",
            name="Regular User",
            email="user@example.com",
            token="user_token_123",
            device_id="device_001",
            device_model="iPhone 13",
            is_admin=False,
            primary_role=UserRole.STUDENT,
            last_login=int(time.time() * 1000)
        )
        
        session.add(admin)
        session.add(regular_user)
        await session.commit()
        
        print("✅ Database seeded successfully!")

# Run: asyncio.run(seed_database())
```

### Test Database Seeding

```python
# tests/fixtures/sample_data.py
import pytest
from app.db.models import User, Note, Task, UserRole, Priority
import time
import uuid

@pytest.fixture
async def admin_user(db_session):
    """Create a test admin user"""
    admin = User(
        id="test_admin_001",
        name="Test Admin",
        email="test_admin@voicenote.com",
        token="admin_test_token",
        device_id="admin_test_device",
        device_model="TestDevice",
        is_admin=True,
        admin_permissions={
            "can_view_all_users": True,
            "can_delete_users": True,
            "can_view_all_notes": True,
            "can_delete_notes": True,
            "can_manage_admins": True,
            "can_view_analytics": True,
            "can_modify_system_settings": True,
            "can_moderate_content": True,
            "can_manage_roles": True,
            "can_export_data": True,
        },
        primary_role=UserRole.DEVELOPER,
        last_login=int(time.time() * 1000)
    )
    db_session.add(admin)
    await db_session.commit()
    return admin

@pytest.fixture
async def regular_user(db_session):
    """Create a test regular user"""
    user = User(
        id="test_user_001",
        name="Test User",
        email="test_user@voicenote.com",
        token="user_test_token",
        device_id="user_test_device",
        device_model="TestDevice",
        is_admin=False,
        primary_role=UserRole.GENERIC,
        last_login=int(time.time() * 1000)
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
async def admin_with_notes(db_session, admin_user):
    """Create admin user with sample notes"""
    note1 = Note(
        id=str(uuid.uuid4()),
        user_id=admin_user.id,
        title="Admin Note 1",
        summary="First admin note",
        timestamp=int(time.time() * 1000),
        status=NoteStatus.PENDING
    )
    note2 = Note(
        id=str(uuid.uuid4()),
        user_id=admin_user.id,
        title="Admin Note 2",
        summary="Second admin note",
        timestamp=int(time.time() * 1000),
        status=NoteStatus.DONE
    )
    db_session.add_all([note1, note2])
    await db_session.commit()
    return admin_user
```

## Running Tests with Test Database

### 1. Setup Test Database
```bash
# Create test database
createdb -U postgres voicenote_test

# Or using psql
psql -U postgres -c "CREATE DATABASE voicenote_test;"
```

### 2. Run Tests
```bash
# Run all tests
pytest tests/

# Run with fixtures
pytest tests/ -v

# Run specific test file
pytest tests/test_users.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### 3. Clean Test Database
```bash
# Drop and recreate
dropdb -U postgres voicenote_test
createdb -U postgres voicenote_test
```

## Database Relationships

```
Users (1) ──→ (N) Notes
  ├── is_admin flag
  ├── admin_permissions JSON
  └── admin_created_at timestamp

Notes (1) ──→ (N) Tasks
  ├── For admin: can view ALL notes across users
  └── For user: can only view own notes

Tasks
  ├── Belongs to specific Note
  └── Can have multiple assignments (flexible JSON)
```

## Performance Optimizations

### Indexes
```sql
-- User lookups
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_is_admin ON users(is_admin) WHERE is_admin = true;

-- Note lookups
CREATE INDEX idx_user_id ON notes(user_id);
CREATE INDEX idx_timestamp ON notes(timestamp);
CREATE INDEX idx_status ON notes(status);

-- Task lookups
CREATE INDEX idx_note_id ON tasks(note_id);
CREATE INDEX idx_deadline ON tasks(deadline);
CREATE INDEX idx_is_done ON tasks(is_done);

-- Vector search
CREATE INDEX idx_embedding ON notes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Connection Pooling
- AsyncPG maintains connection pool automatically
- Default pool size: 10 connections
- Max overflow: 10 additional connections
- Auto-recycles connections after 3600 seconds

### Query Optimization
- Eager loading for relationships when needed
- Pagination for large result sets (20 items/page default)
- Soft deletes to preserve data integrity
- Timestamp-based sorting for performance

## Migration Management

### Using Alembic (Future)
```bash
# Initialize migrations
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add admin role"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Monitoring & Debugging

### Enable Query Logging
```python
# In session.py
engine = create_async_engine(DATABASE_URL, echo=True)  # Shows all SQL queries
```

### Check Connection Pool Status
```python
from sqlalchemy.pool import QueuePool
pool_size = engine.pool.size()
checked_out = engine.pool.checkedout()
overflow = engine.pool.overflow()
```

### Database Size
```sql
SELECT pg_size_pretty(pg_database_size('voicenote'));
SELECT pg_size_pretty(pg_total_relation_size('public.notes'));
```

## Backup & Recovery

### Backup Production Database
```bash
pg_dump -U postgres -d voicenote > voicenote_backup.sql
```

### Restore from Backup
```bash
psql -U postgres -d voicenote < voicenote_backup.sql
```

### Backup Frequency
- Daily full backups
- Hourly incremental backups (via WAL)
- 30-day retention policy

## Disaster Recovery

### RTO (Recovery Time Objective): 1 hour
### RPO (Recovery Point Objective): 15 minutes

1. Switch to standby PostgreSQL instance
2. Apply WAL recovery
3. Point application to new database
4. Verify data integrity
5. Document incident

