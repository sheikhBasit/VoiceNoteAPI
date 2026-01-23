from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Async URL for FastAPI async endpoints if needed
ASYNC_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@db:5432/voicenote")

# Sync URL for synchronous SQLAlchemy (most of our current code uses this)
# Replace asyncpg with psycopg2 for sync usage
SYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("+asyncpg", "")

# Async Setup
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync Setup (Required for current API implementation and Celery workers)
sync_engine = create_engine(SYNC_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://"), echo=False)
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