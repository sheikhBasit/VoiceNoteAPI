from unittest.mock import MagicMock, patch
import sys
import os

# Mock AI clients at module level
sys.modules["deepgram"] = MagicMock()
sys.modules["deepgram.core"] = MagicMock()
sys.modules["deepgram.core.api_error"] = MagicMock()
sys.modules["groq"] = MagicMock()
sys.modules["pyannote"] = MagicMock()
sys.modules["pyannote.audio"] = MagicMock()

# Force local DB connection for standalone verification
os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5433/voicenote"

from app.main import app
from app.db.session import SessionLocal, sync_engine as engine
from app.db import models
from app.services.billing_service import BillingService
from app.services.meeting_service import MeetingService
import json
import uuid

def run_standalone_tests():
    print("🚀 Starting Standalone Enterprise Verification...")
    db = SessionLocal()
    try:
        # Test 1: Wallet Creation
        user_id = f"standalone_user_{uuid.uuid4()}"
        
        # Create User first (FK Requirement)
        user = models.User(id=user_id, email=f"{user_id}@test.com", name="Enterprise User")
        db.add(user)
        db.commit()
        
        billing = BillingService(db)
        wallet = billing.get_or_create_wallet(user_id)
        assert wallet.balance == 100
        print(f"✅ Wallet Creation Verified: {user_id}")

        # Test 2: Usage Charge
        billing.charge_usage(user_id, 25, "AI Generation Case")
        wallet = db.query(models.Wallet).filter(models.Wallet.user_id == user_id).first()
        assert wallet.balance == 75
        print(f"✅ Usage Charge Logic Verified: Balance is {wallet.balance}")

        # Test 3: Meeting Bot Synthesis
        service = MeetingService(db)
        # We need a user record for FK
        user = models.User(id=user_id, email=f"{user_id}@test.com", name="Enterprise User")
        db.add(user)
        db.commit()

        service.handle_webhook_event({
            "event": "bot.leave",
            "data": {
                "bot_id": "bot_999",
                "bot": {"metadata": {"user_id": user_id}},
                "transcript": "Enterprise transcript content for standalone verification."
            }
        })
        
        note = db.query(models.Note).filter(models.Note.user_id == user_id).first()
        assert note is not None
        assert "Enterprise" in note.transcript_groq
        print(f"✅ Meeting Bot Auto-Synthesis Verified: Note ID {note.id}")

        print("\n🏆 ALL ENTERPRISE TESTS PASSED (STANDALONE) 🏆")

    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_standalone_tests()
