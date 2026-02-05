import pytest
import sys
import os
import json
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

# Load .env dynamically based on project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

# Force local DB connection for pytest if not in Docker/CI
if not os.getenv("DATABASE_URL") or "localhost" in os.getenv("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:password@localhost:5433/voicenote_test"

# Force Celery to be eager in tests to avoid connection errors
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "True"
os.environ["ENVIRONMENT"] = "testing"
# Force Redis to memory for tests to avoid connection errors
os.environ["REDIS_URL"] = "memory://"

# Force dummy API keys to ensure AI clients are initialized (they will be mocked)
os.environ["GROQ_API_KEY"] = "mock-key-for-testing"
os.environ["DEEPGRAM_API_KEY"] = "mock-key-for-testing"
os.environ["ENABLE_AI_PIPELINES"] = "true"

from app.db.session import SessionLocal, sync_engine as engine
from app.db.models import Base  # This registers all models on Base.metadata

@pytest.fixture(scope="session", autouse=True)
def mock_ai_services():
    """Globally mock AI services for all tests."""
    from unittest.mock import patch, MagicMock
    
    # 1. Mock sentence_transformers
    mock_st = MagicMock()
    mock_st_model = MagicMock()
    # Mocking numpy-like behavior
    mock_embedding = MagicMock()
    mock_embedding.tolist.return_value = [0.0] * 384
    mock_st_model.encode.return_value = mock_embedding
    mock_st.SentenceTransformer.return_value = mock_st_model
    sys.modules["sentence_transformers"] = mock_st
    
    # 2. Mock Deepgram
    mock_dg = MagicMock()
    sys.modules["deepgram"] = mock_dg
    sys.modules["deepgram.core"] = MagicMock()
    sys.modules["deepgram.core.api_error"] = MagicMock()
    
    # 3. Mock Groq
    mock_groq_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "summary": "This is a test summary",
        "title": "Test Note",
        "priority": "MEDIUM",
        "topics": ["test"],
        "entities": [],
        "action_items": [],
        "sentiment": "neutral",
        "key_points": ["point 1"],
        "project_association": "None",
        "tasks": [{"description": "Action item", "priority": "HIGH", "deadline": None}],
        "emotional_tone": "Neutral",
        "logical_patterns": [],
        "suggested_questions": []
    })
    mock_groq_client.chat.completions.create.return_value = mock_response
    mock_groq_client.audio.transcriptions.create.return_value = "Mock Transcript"
    
    # Patch Groq where it's used to avoid import timing issues
    patchers = [
        patch("groq.Groq", return_value=mock_groq_client),
        patch("app.services.ai_service.Groq", return_value=mock_groq_client, create=True)
    ]
    for p in patchers: p.start()
        
    yield
    
    for p in patchers: p.stop()

@pytest.fixture(scope="session", autouse=True)
def setup_db(mock_ai_services): 
    """Create a fresh database schema for the test session."""
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"DEBUG: setup_db - FAILED with error: {e}")
        raise
    
    yield
    # No drop_all at end to avoid issues with concurrent runs

@pytest.fixture
def db():
    """Provides a clean database session for each test function."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def db_session(db):
    return db

@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)

@pytest.fixture
async def async_client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
