import json
import os
import sys

# Set env vars BEFORE importing app modules
os.environ["ENVIRONMENT"] = "testing"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REDIS_URL"] = "memory://"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["MINIO_ENDPOINT"] = "localhost:9000"
os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
os.environ["MINIO_SECRET_KEY"] = "minioadmin"
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/models"
from unittest.mock import MagicMock, AsyncMock

import pytest
from app.db.session import get_db


# --- MOCK LIBS BEFORE IMPORTS ---
def mock_package(name):
    mock = MagicMock()
    mock.__path__ = []
    mock.__all__ = []
    mock.__spec__ = MagicMock()  # Fix for Python 3.11+
    sys.modules[name] = mock
    return mock


# Surgical mocks for problematic packages
redis_mock = mock_package("redis")
redis_mock.__version__ = "5.0.0"
mock_package("redis.client")
mock_package("redis.connection")
redis_asyncio = mock_package("redis.asyncio")

# Configure Async Redis Client
redis_client_mock = MagicMock()
redis_client_mock.get = AsyncMock(return_value=None)
redis_client_mock.set = AsyncMock(return_value=True)
redis_client_mock.delete = AsyncMock(return_value=1)
redis_client_mock.exists = AsyncMock(return_value=0)
redis_client_mock.expire = AsyncMock(return_value=True)
redis_client_mock.publish = AsyncMock(return_value=1)
redis_client_mock.ping = AsyncMock(return_value=True)
redis_client_mock.close = AsyncMock(return_value=None)

redis_asyncio.from_url.return_value = redis_client_mock
redis_asyncio.Redis.return_value = redis_client_mock

# pgvector Mock for SQLite
mock_pgvector = mock_package("pgvector")
mock_pg_sql = mock_package("pgvector.sqlalchemy")
from sqlalchemy import String, literal_column


class MockVector(String):
    class comparator_factory(String.Comparator):
        def cosine_distance(self, other):
            return literal_column("'0'")
            
        def l2_distance(self, other):
            return literal_column("'0'")


mock_pg_sql.Vector = MockVector

# Handle JSONB for SQLite
import sqlalchemy.dialects.postgresql
from sqlalchemy.types import JSON

sqlalchemy.dialects.postgresql.JSONB = JSON

# Heavy/External AI mocks - Only mock if absolutely necessary
# For now, let's keep sentence_transformers and transformers mocked as they are very heavy
mock_package("sentence_transformers")
mock_package("transformers")
mock_torch = mock_package("torch")


class MockTensor:
    pass


mock_torch.Tensor = MockTensor

# Global Mocks with Configuration (MUST be before app imports)
# 1. Minio
mock_minio = mock_package("minio")
mock_minio.Minio.return_value.presigned_put_object.return_value = (
    "http://minio/bucket/key"
)
mock_package("minio.error")

# 2. Deepgram
mock_dg = mock_package("deepgram")
mock_dg_client = mock_dg.DeepgramClient.return_value
mock_dg_client.listen.prerecorded.v.transcribe_file.return_value = MagicMock(
    to_json=lambda: json.dumps(
        {
            "results": {
                "channels": [{"alternatives": [{"transcript": "Deepgram Transcript"}]}]
            }
        }
    )
)

# 3. Groq
mock_groq = mock_package("groq")
mock_groq_client = mock_groq.Groq.return_value
mock_groq_resp = MagicMock()
mock_groq_resp.choices = [MagicMock()]
mock_groq_resp.choices[0].message.content = json.dumps(
    {
        "summary": "Mock Summary",
        "title": "Mock Title",
        "priority": "MEDIUM",
        "tasks": [],
        "topics": [],
        "sentiment": "neutral",
        "key_points": [],
        "project_association": "None",
        "entities": [],
        "action_items": [],
        "emotional_tone": "Neutral",
        "logical_patterns": [],
        "suggested_questions": [],
    }
)
mock_groq_client.chat.completions.create.return_value = mock_groq_resp
mock_groq_client.audio.transcriptions.create.return_value = MagicMock(
    text="Groq Transcript"
)

# 4. Stripe
mock_stripe = mock_package("stripe")
mock_stripe.api_key = "sk_test_mock"

# Global Celery Mock
from celery import Celery

Celery.apply_async = MagicMock()
Celery.send_task = MagicMock()
Celery.on_init = MagicMock()
# Also mock Task.delay
from celery.app.task import Task

Task.delay = MagicMock()
Task.apply_async = MagicMock()

# Handle pydub

# ---------------------------------

# Mock AI Models path


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup environment variables for testing"""
    # Create test DB
    import app.db.models  # Register models
    from app.db.session import Base
    from app.db.session import sync_engine as engine

    if os.path.exists("./test.db"):
        os.remove("./test.db")

    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture
def db_session():
    """Provides a fresh database session for each test"""
    from app.db.session import SessionLocal, Base
    session = SessionLocal()
    
    # Clean up any existing data before starting the test
    # SQLite doesn't support TRUNCATE, so we use DELETE from all tables
    # following the dependency graph order (reversed sorted_tables)
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    except Exception:
        session.rollback()
        
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def db(db_session):
    """Alias for db_session to support tests that use 'db'"""
    return db_session


@pytest.fixture
async def async_client():
    """Provides an asynchronous HTTP client for testing"""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def client(db_session):
    """Provides a synchronous TestClient for testing"""
    from fastapi.testclient import TestClient
    from app.main import app
    # Override get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_ai_services():
    """Mock external AI services centrally (Legacy patch cleanup)"""
    
    # Retrieve the current mock objects dynamically to avoid stale references
    groq_mod = sys.modules.get("groq")
    if groq_mod:
        client_mock = groq_mod.Groq.return_value
        
        # Reset Groq mock to default state
        client_mock.chat.completions.create.reset_mock(return_value=True, side_effect=True)
        client_mock.audio.transcriptions.create.reset_mock(return_value=True, side_effect=True)
        
        default_response = MagicMock()
        default_response.choices = [MagicMock()]
        default_response.choices[0].message.content = json.dumps(
            {
                "summary": "Mock Summary",
                "title": "Mock Title",
                "priority": "MEDIUM",
                "tasks": [],
                "topics": [],
                "sentiment": "neutral",
                "key_points": [],
                "project_association": "None",
                "entities": [],
                "action_items": [],
                "emotional_tone": "Neutral",
                "logical_patterns": [],
                "suggested_questions": [],
                # Add fields expected by search
                "answer": "Mock Answer", 
                "query": "Mock Query",
                "source": "Mock Source"
            }
        )
        client_mock.chat.completions.create.return_value = default_response
        client_mock.chat.completions.create.side_effect = None
        
        client_mock.audio.transcriptions.create.return_value = MagicMock(text="Groq Transcript")

    # Reset Singleton state in AIService to ensure it picks up the correct mock
    from app.services.ai_service import AIService
    AIService._groq_client = None
    AIService._dg_client = None
    
    yield


@pytest.fixture(autouse=True)
def mock_broadcaster_redis():
    """Ensure broadcaster redis is async compatible"""
    try:
        from app.services.broadcaster import broadcaster
        # Directly patch the instance method if it's not already an AsyncMock
        if not isinstance(broadcaster.redis.get, AsyncMock):
            broadcaster.redis.get = AsyncMock(return_value=None)
            broadcaster.redis.set = AsyncMock(return_value=True)
            broadcaster.redis.delete = AsyncMock(return_value=1)
            broadcaster.redis.publish = AsyncMock(return_value=1)
            broadcaster.redis.expire = AsyncMock(return_value=True)
            broadcaster.redis.exists = AsyncMock(return_value=0)
    except ImportError:
        pass
    yield
