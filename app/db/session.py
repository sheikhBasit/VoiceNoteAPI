from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Load environment variables
# Only load .env if not running in a container
if not os.path.exists("/.dockerenv") and os.path.exists(".env"):
    load_dotenv()

# Async URL for FastAPI async endpoints if needed
# Async URL for FastAPI async endpoints
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@db:5432/voicenote")

if DATABASE_URL.startswith("sqlite"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://") if "aiosqlite" not in DATABASE_URL else DATABASE_URL
    SYNC_DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")
    connect_args = {"check_same_thread": False}
else:
    # Handle CASE: DATABASE_URL might already have +asyncpg
    clean_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
    ASYNC_DATABASE_URL = clean_url.replace("postgresql://", "postgresql+asyncpg://")
    SYNC_DATABASE_URL = clean_url.replace("postgresql://", "postgresql+psycopg2://")
    connect_args = {}

# Async Setup
async_engine = None
AsyncSessionLocal = None

if "sqlite" not in ASYNC_DATABASE_URL or os.getenv("USE_ASYNCSQLITE", "false") == "true":
    try:
        async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, connect_args=connect_args if "sqlite" in ASYNC_DATABASE_URL else {})
        AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    except ImportError:
        pass # aiosqlite not installed, logic falls back to sync if no async endpoints called

# Sync Setup
sync_engine = create_engine(
    SYNC_DATABASE_URL, 
    echo=False, 
    connect_args=connect_args if "sqlite" in SYNC_DATABASE_URL else {},
    pool_size=20, # Increased from default 5
    max_overflow=10, 
    pool_pre_ping=True, # Verify connection health before use
    pool_recycle=3600 # Prevent stale connections
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

# FastAPI Dependency (Sync version)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# FastAPI Dependency (Async version - if needed in future)
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session