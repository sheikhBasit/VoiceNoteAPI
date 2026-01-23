import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.session import get_db, Base

import os

# Use a separate test database
if os.path.exists("/.dockerenv"):
    DEFAULT_TEST_DB = "postgresql+asyncpg://postgres:password@db:5432/voicenote_test"
else:
    DEFAULT_TEST_DB = "postgresql+asyncpg://postgres:password@localhost:5432/voicenote_test"

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_DB)


engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session", autouse=True)
async def initialize_db(request):
    """Create a fresh database schema for the test session."""
    
    # Check if this is a standalone test file
    try:
        test_file = str(request.fspath) if hasattr(request, 'fspath') else ""
    except:
        test_file = ""
    
    # Skip for standalone test files
    is_standalone = any(name in test_file for name in [
        'test_advanced_performance.py',
        'test_security_attacks.py',
        'test_endpoint_load.py',
        'test_phase1_standalone.py'
    ])
    
    if is_standalone:
        yield
        return
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Cleanup (optional, usually we want to keep it if we reuse the volume)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Provides a clean database session for each test function."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    """Async client for testing FastAPI endpoints."""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac