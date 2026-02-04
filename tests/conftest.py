import pytest
import sys
import os
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

from app.db.session import SessionLocal, sync_engine as engine
from app.db.models import Base

# --- GLOBAL AI MOCKS ---
# These must be set before any app modules are imported
sys.modules["deepgram"] = MagicMock()
sys.modules["deepgram.core"] = MagicMock()
sys.modules["deepgram.core.api_error"] = MagicMock()
sys.modules["groq"] = MagicMock()
sys.modules["pyannote"] = MagicMock()
sys.modules["pyannote.audio"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()
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
