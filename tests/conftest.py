import json
import os
import sys
from unittest.mock import MagicMock

import pytest


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
mock_package("redis.asyncio")

# pgvector Mock for SQLite
mock_pgvector = mock_package("pgvector")
mock_pg_sql = mock_package("pgvector.sqlalchemy")
from sqlalchemy import String, literal_column


class MockVector(String):
    class comparator_factory(String.Comparator):
        def cosine_distance(self, other):
            return literal_column("'0'")


mock_pg_sql.Vector = MockVector

# Handle JSONB for SQLite
import sqlalchemy.dialects.postgresql
from sqlalchemy.types import JSON

sqlalchemy.dialects.postgresql.JSONB = JSON

# Heavy/External AI mocks
mock_package("pydub")
mock_package("pydub.silence")
mock_package("pydub.audio_segment")
mock_package("librosa")
mock_package("soundfile")
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
mock_pydub = mock_package("pydub")
mock_package("pydub.silence")
mock_package("pydub.audio_segment")

# ---------------------------------

# Set env vars BEFORE importing app modules
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REDIS_URL"] = "memory://"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["MINIO_ENDPOINT"] = "localhost:9000"
os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
os.environ["MINIO_SECRET_KEY"] = "minioadmin"
# Mock AI Models path
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/models"


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
    from app.db.session import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def mock_ai_services():
    """Mock external AI services centrally (Legacy patch cleanup)"""
    # Using global mocks now, but keeping this for any localized patching if needed
    yield
