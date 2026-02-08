
import os
import sys
import uvicorn
from unittest.mock import MagicMock
from importlib import MockModule
# --- 1. SET ENV VARS ---
os.environ["DATABASE_URL"] = "sqlite:///./benchmark.db"
os.environ["REDIS_URL"] = "memory://"
os.environ["ENVIRONMENT"] = "benchmark"

# --- 2. MOCK HEAVY/MISSING LIBRARIES ---
# Common mock for audio
MOCK_AUDIO = MagicMock()
MOCK_AUDIO.dBFS = -20
MOCK_AUDIO.__len__.return_value = 1000
MOCK_AUDIO.__add__.return_value = MOCK_AUDIO

def get_mock():
    m = MagicMock()
    m.load.return_value = ([], 16000)
    m.trim.return_value = ([], 16000)
    m.resample.return_value = ([], 16000)
    m.effects.trim.return_value = ([], 16000)
    
    # AudioSegment class methods
    m.AudioSegment.from_file.return_value = MOCK_AUDIO
    m.AudioSegment.from_wav.return_value = MOCK_AUDIO
    m.from_file.return_value = MOCK_AUDIO
    m.from_wav.return_value = MOCK_AUDIO
    
    # pydub.effects
    m.normalize.return_value = MOCK_AUDIO
    m.compress_dynamic_range.return_value = MOCK_AUDIO
    
    return m

COMMON_MOCK = get_mock()

# Only mock what's actually missing or broken
missing_broken = ["sentence_transformers", "pydub", "pydub.audio_segment", "pydub.effects", "noisereduce", "librosa", "librosa.display", "librosa.effects"]
for mod in missing_broken:
    sys.modules[mod] = COMMON_MOCK

# Mock the entire audio processing module to avoid library issues
import app.core.audio
app.core.audio.preprocess_audio_pipeline = lambda x: x
sys.modules["app.core.audio"] = app.core.audio

# Fix for deepgram import issue
try:
    import deepgram
except ImportError:
    sys.modules["deepgram"] = MockModule()

# --- 3. MOCK DATABASE TYPES FOR SQLITE ---
import sqlalchemy.types
import sqlalchemy.dialects.postgresql

class MockVector(sqlalchemy.types.TypeDecorator):
    impl = sqlalchemy.types.String
    cache_ok = True
    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(sqlalchemy.types.String)

# Mock pgvector if not installed
try:
    import pgvector.sqlalchemy
except ImportError:
    pgvector_mod = MockModule()
    pgvector_mod.Vector = MockVector
    sys.modules["pgvector"] = pgvector_mod
    sys.modules["pgvector.sqlalchemy"] = pgvector_mod

# Mock JSONB for SQLite
sqlalchemy.dialects.postgresql.JSONB = sqlalchemy.types.JSON

# --- 4. IMPORT APP ---
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from app.main import app
    from app.db.session import sync_engine, Base
    import app.db.models as models
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)

# --- 5. SETUP DB ---
print("Creating tables...")
Base.metadata.create_all(bind=sync_engine)
print("Tables created.")

# Seed Admin User
with sync_engine.connect() as conn:
    from sqlalchemy import insert
    import uuid
    import time
    admin_id = "bench-admin-id"
    # Check if exists
    res = conn.execute(sqlalchemy.text(f"SELECT id FROM users WHERE email = 'admin@voicenote.api'")).fetchone()
    if not res:
        conn.execute(sqlalchemy.text(f"""
            INSERT INTO users (id, name, email, is_admin, tier, last_login, is_deleted, primary_role, jargons, work_start_hour, work_end_hour, work_days)
            VALUES ('{admin_id}', 'Admin User', 'admin@voicenote.api', 1, 'FREE', {int(time.time()*1000)}, 0, 'GENERIC', '[]', 9, 17, '[2,3,4,5,6]')
        """))
        # Wallet
        conn.execute(sqlalchemy.text(f"INSERT INTO wallets (user_id, balance, currency) VALUES ('{admin_id}', 1000000, 'USD')"))
        conn.commit()
    print("Admin user seeded: admin@voicenote.api / (no password check in benchmark auth mock)")

# --- 6. RUN SERVER ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="error")
