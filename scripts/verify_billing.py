
import concurrent.futures
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, "/mnt/muaaz/VoiceNoteAPI")

from unittest.mock import MagicMock
# --- MOCK LIBS BEFORE IMPORTS ---
def mock_package(name):
    mock = MagicMock()
    mock.__path__ = []
    mock.__all__ = []
    mock.__spec__ = MagicMock()
    sys.modules[name] = mock
    return mock

# Surgical mocks for problematic packages
redis_mock = mock_package("redis")
mock_package("redis.client")
mock_package("redis.connection")
mock_package("redis.asyncio")

# pgvector Mock for SQLite
mock_pgvector = mock_package("pgvector")
mock_pg_sql = mock_package("pgvector.sqlalchemy")
from sqlalchemy import String, literal_column

from sqlalchemy.types import UserDefinedType

class MockVector(UserDefinedType):
    def __init__(self, dim=None):
        self.dim = dim
    def get_col_spec(self, **kw):
        return f"vector({self.dim})" if self.dim else "vector"
    class comparator_factory(UserDefinedType.Comparator):
        def cosine_distance(self, other):
            return literal_column("'0'")
        def l2_distance(self, other):
            return literal_column("'0'")

mock_pg_sql.Vector = MockVector

# Handle JSONB - use real JSONB for PostgreSQL
import sqlalchemy.dialects.postgresql
from sqlalchemy.dialects.postgresql import JSONB
sqlalchemy.dialects.postgresql.JSONB = JSONB

# Heavy/External AI mocks
mock_package("pydub")
mock_package("pydub.silence")
mock_package("pydub.audio_segment")
mock_package("librosa")
mock_package("soundfile")
mock_package("sentence_transformers")
mock_package("transformers")
mock_torch = mock_package("torch")
mock_torch.Tensor = MagicMock()
mock_package("minio")
mock_package("deepgram")
mock_package("groq")
mock_stripe = mock_package("stripe")
mock_stripe.api_key = "sk_test_mock"
from celery import Celery
Celery.send_task = MagicMock()

# Set env vars 
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:////tmp/billing_test.db"
os.environ["REDIS_URL"] = "memory://"

from app.db import models
from app.services.billing_service import BillingService

class TestBillingConcurrency:
    """Test concurrent billing operations."""

    @pytest.fixture(scope="module")
    def custom_db(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db.session import Base
        
        # Use PostgreSQL for row-level locking support
        db_url = "postgresql://postgres:password@localhost:5433/voicenote_test_billing"
        
        # Create a test database if it doesn't exist (using sync engine)
        from sqlalchemy import create_engine, text
        admin_engine = create_engine("postgresql://postgres:password@localhost:5433/postgres")
        with admin_engine.connect() as conn:
            conn.execute(text("COMMIT"))  # Close transaction
            try:
                conn.execute(text("CREATE DATABASE voicenote_test_billing"))
            except Exception:
                pass # Already exists
        
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text("COMMIT"))
            
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        yield TestingSessionLocal
        
        # Cleanup - Drop tables to start fresh next time
        Base.metadata.drop_all(bind=engine)

    @pytest.mark.load
    def test_concurrent_wallet_deduction(self, custom_db):
        """
        Verify atomicity of wallet deductions.
        Start with 100 credits.
        Launch 10 concurrent threads each deducting 10 credits.
        Final balance should be 0.
        If race condition exists, balance will be > 0 (lost updates).
        """
        # 1. Setup User and Wallet
        db_session = custom_db()
        try:
            user_id = "concurrent_user"
            user = models.User(id=user_id, email="concurrent@test.com", name="Concurrent User")
            db_session.add(user)
            
            # Create wallet with 100 credits
            wallet = models.Wallet(user_id=user_id, balance=100)
            db_session.add(wallet)
            db_session.commit()
        finally:
            db_session.close()

        # 2. Define concurrent operation
        def charge_wallet():
            # Each thread needs its own session to simulate concurrent transactions
            session = custom_db()
            try:
                billing = BillingService(session)
                # Charge 10 credits
                success = billing.charge_usage(user_id, cost=10, description="Concurrent Charge")
                return success
            finally:
                session.close()

        # 3. Execute concurrently
        workers = 10
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(charge_wallet) for _ in range(workers)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # 4. Verify results
        # All charges should succeed
        assert all(results), "Some charges failed unexpectedly"
        
        # 5. Check final balance
        # Must refresh wallet from DB
        check_session = custom_db()
        final_wallet = check_session.query(models.Wallet).filter_by(user_id=user_id).first()
        
        print(f"\n💰 Initial Balance: 100")
        print(f"   Charges: {workers} x 10 = {workers*10}")
        print(f"   Final Balance: {final_wallet.balance}")
        
        assert final_wallet.balance == 0, f"Race condition detected! Balance {final_wallet.balance} != 0"
        check_session.close()

    @pytest.mark.load
    def test_concurrent_overdraft_prevention(self, custom_db):
        """
        Verify that we cannot overdraft the wallet concurrently.
        Start with 50 credits.
        Launch 10 concurrent threads each trying to deduct 10 credits.
        Only 5 should succeed. Balance should be 0.
        """
        # 1. Setup User and Wallet
        db_session = custom_db()
        try:
            user_id = "overdraft_user"
            user = models.User(id=user_id, email="overdraft@test.com", name="Overdraft User")
            db_session.add(user)
            
            # Create wallet with 50 credits
            wallet = models.Wallet(user_id=user_id, balance=50)
            db_session.add(wallet)
            db_session.commit()
        finally:
            db_session.close()

        # 2. Define concurrent operation
        def charge_wallet():
            session = custom_db()
            try:
                billing = BillingService(session)
                # Charge 10 credits
                success = billing.charge_usage(user_id, cost=10, description="Concurrent Charge")
                return success
            finally:
                session.close()

        # 3. Execute concurrently
        workers = 10
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(charge_wallet) for _ in range(workers)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # 4. Verify results
        success_count = sum(results)
        print(f"\n🛑 Overdraft Test:")
        print(f"   Attempts: {workers}")
        print(f"   Successes: {success_count} (Expected 5)")
        
        # 5. Check final balance
        check_session = custom_db()
        final_wallet = check_session.query(models.Wallet).filter_by(user_id=user_id).first()
        print(f"   Final Balance: {final_wallet.balance}")

        assert success_count == 5, f"Expected 5 successful charges, got {success_count}"
        assert final_wallet.balance == 0, "Balance should be exhausted exactly to 0"
        check_session.close()
