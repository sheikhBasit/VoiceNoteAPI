import pytest
import sys
from unittest.mock import MagicMock
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
# sys.modules["sentence_transformers"] = MagicMock()
# sys.modules["noisereduce"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["numpy"] = MagicMock()

# Configure SentenceTransformer Mock
mock_st = MagicMock()
mock_model = MagicMock()
# Support .encode().tolist() chain
mock_model.encode.return_value.tolist.return_value = [0.1] * 384
mock_st.SentenceTransformer.return_value = mock_model
sys.modules["sentence_transformers"] = mock_st

# Configure NoiseReduce Mock
mock_nr = MagicMock()
# Return a fake "numpy array" that soundfile can write (if mocked) or just pass through
mock_nr.reduce_noise.return_value = MagicMock() 
sys.modules["noisereduce"] = mock_nr

# Mock Soundfile to avoid IO and numpy dependency issues
sys.modules["soundfile"] = MagicMock()

import os
# Force local DB connection for pytest
os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5433/voicenote"

from app.db.session import SessionLocal, sync_engine as engine
from app.db.models import Base
@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create a fresh database schema for the test session."""
    Base.metadata.create_all(bind=engine)
    yield
    # Base.metadata.drop_all(bind=engine)
    # Base.metadata.drop_all(bind=engine)

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
