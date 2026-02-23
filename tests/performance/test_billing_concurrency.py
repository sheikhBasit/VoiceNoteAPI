"""
Billing concurrency tests.

Verifies that wallet deductions are atomic and overdraft prevention works
under concurrent load.

IMPORTANT: These tests require PostgreSQL because SQLite silently ignores
SELECT … FOR UPDATE, making the lock tests meaningless. They are automatically
skipped when PostgreSQL is not reachable.

Run with: pytest tests/performance/ -v -m load
      OR: docker exec voicenote_api python -m pytest tests/performance/ -v
"""

import concurrent.futures
import os

import pytest

from app.db import models
from app.services.billing_service import BillingService


# ---------------------------------------------------------------------------
# Module-level skip guard — skip when PostgreSQL is not reachable
# (SQLite does not support SELECT … FOR UPDATE; locking tests are meaningless)
# ---------------------------------------------------------------------------

_PG_URL = "postgresql://postgres:password@localhost:5433/voicenote"


def _postgres_is_up() -> bool:
    """Return True if the project's PostgreSQL instance is reachable."""
    try:
        import sqlalchemy

        engine = sqlalchemy.create_engine(
            _PG_URL, connect_args={"connect_timeout": 3}
        )
        with engine.connect():
            pass
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_is_up(),
    reason=(
        "Billing concurrency tests require PostgreSQL (FOR UPDATE support). "
        "SQLite is not supported. Start the Docker DB: docker compose up -d db"
    ),
)


class TestBillingConcurrency:
    """Test concurrent billing operations."""

    @pytest.fixture(scope="module")
    def custom_db(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db.session import Base

        # Always use PostgreSQL — SQLite ignores FOR UPDATE
        engine = create_engine(_PG_URL)
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        yield TestingSessionLocal

        engine.dispose()


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
            import uuid
            user_id = f"concurrent_user_{uuid.uuid4().hex[:8]}"
            user = models.User(id=user_id, email=f"{user_id}@test.com", name="Concurrent User")
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
        db_session.expire_all()
        final_wallet = db_session.query(models.Wallet).filter_by(user_id=user_id).first()
        
        print(f"\n💰 Initial Balance: 100")
        print(f"   Charges: {workers} x 10 = {workers*10}")
        print(f"   Final Balance: {final_wallet.balance}")
        
        assert final_wallet.balance == 0, f"Race condition detected! Balance {final_wallet.balance} != 0"

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
            import uuid
            user_id = f"overdraft_user_{uuid.uuid4().hex[:8]}"
            user = models.User(id=user_id, email=f"{user_id}@test.com", name="Overdraft User")
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
