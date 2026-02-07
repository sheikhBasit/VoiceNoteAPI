"""
Integration test configuration and global mocks.
"""

import sys
from unittest.mock import MagicMock

from sqlalchemy.types import UserDefinedType

# --- High-Level Mocks to stop dependency chain ---

# Mock the entire service and worker modules before they are imported
mock_worker = MagicMock()
sys.modules["app.worker.task"] = mock_worker

mock_ai_service = MagicMock()
sys.modules["app.services.ai_service"] = mock_ai_service

# Mock other external heavy deps that might still be hit
sys.modules["torch"] = MagicMock()
sys.modules["torch.nn"] = MagicMock()
sys.modules["deepgram"] = MagicMock()
sys.modules["groq"] = MagicMock()
sys.modules["pyannote"] = MagicMock()
sys.modules["pyannote.audio"] = MagicMock()
sys.modules["cloudinary"] = MagicMock()
sys.modules["cloudinary.uploader"] = MagicMock()


# Mock pgvector for SQLAlchemy Column initialization
class MockVector(UserDefinedType):
    def __init__(self, dim=None):
        self.dim = dim

    def get_col_spec(self, **kw):
        return "TEXT"

    def bind_processor(self, dialect):
        return lambda x: str(x)

    def result_processor(self, dialect, coltype):
        return lambda x: x


mock_vector_mod = MagicMock()
mock_vector_mod.Vector = MockVector
sys.modules["pgvector"] = mock_vector_mod
sys.modules["pgvector.sqlalchemy"] = mock_vector_mod
