import pytest
import sys
import os
import json
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Load .env dynamically based on project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

# Force local DB connection for pytest if not in Docker/CI
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/voicenote"

# Force Celery to be eager in tests to avoid connection errors
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "True"
os.environ["ENVIRONMENT"] = "testing"
# Force Redis to memory for tests to avoid connection errors
os.environ["REDIS_URL"] = "memory://"

# Force dummy API keys to ensure AI clients are initialized (they will be mocked)
os.environ["GROQ_API_KEY"] = "mock-key-for-testing"
os.environ["DEEPGRAM_API_KEY"] = "mock-key-for-testing"
os.environ["ENABLE_AI_PIPELINES"] = "true" # Ensure lazy loading paths are hit if needed

if os.getenv("GITHUB_ACTIONS") == "true":
    print("DEBUG: conftest.py initialized in GITHUB_ACTIONS")
    print(f"DEBUG: CELERY_TASK_ALWAYS_EAGER={os.environ['CELERY_TASK_ALWAYS_EAGER']}")

from app.db.session import SessionLocal, sync_engine as engine
from app.db.models import Base

# --- GLOBAL AI MOCKS ---
# These must be set before any app modules are imported
# Mock AI libraries defensively
mock_st = MagicMock()
mock_st_model = MagicMock()
mock_st_model.encode.return_value = [0.0] * 384 # Standard for all-MiniLM-L6-v2
mock_st.SentenceTransformer.return_value = mock_st_model
sys.modules["sentence_transformers"] = mock_st

sys.modules["deepgram"] = MagicMock()
sys.modules["deepgram.core"] = MagicMock()
sys.modules["deepgram.core.api_error"] = MagicMock()

# Mock Groq to return valid JSON structure
mock_groq = MagicMock()
mock_groq_client = MagicMock()
mock_response = MagicMock()
mock_response.choices = [MagicMock()]
# Ensure the mock object has a content attribute that is a string
mock_response.choices[0].message.content = json.dumps({
    "summary": "This is a test summary",
    "topics": ["test"],
    "entities": [],
    "action_items": [],
    "sentiment": "neutral"
})
mock_groq_client.chat.completions.create.return_value = mock_response
mock_groq.Groq.return_value = mock_groq_client
sys.modules["groq"] = mock_groq

sys.modules["pyannote"] = MagicMock()
sys.modules["pyannote.audio"] = MagicMock()
sys.modules["noisereduce"] = MagicMock()
# sys.modules["torch"] = MagicMock()
# sys.modules["numpy"] = MagicMock()

# Configure SentenceTransformer Mock - REMOVED (Use real)
# Configure NoiseReduce Mock - REMOVED (Use real)
# Mock Soundfile - REMOVED (Use real)

# from app.db.session import SessionLocal, sync_engine as engine
# from app.db.models import Base
@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create a fresh database schema for the test session."""
    with engine.connect() as conn:
        from sqlalchemy import text
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    
    Base.metadata.drop_all(bind=engine) # Ensure clean start
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine) # Cleanup after

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
    """Alias for db fixture to support legacy tests."""
    return db
