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
sys.modules["torch"] = MagicMock()
sys.modules["numpy"] = MagicMock()

import os
# Force local DB connection for pytest
os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5433/voicenote"

from app.db.session import SessionLocal, sync_engine as engine
from app.db.models import Base
    """Create a fresh database schema for the test session."""
    Base.metadata.create_all(bind=engine)
    yield
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
