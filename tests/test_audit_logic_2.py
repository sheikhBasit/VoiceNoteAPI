import hmac
import hashlib
import time
import pytest
from unittest.mock import MagicMock
from fastapi import Request, HTTPException

# 1. Test Signature Hardening
@pytest.mark.asyncio
async def test_device_signature_with_query():
    from app.utils.security import verify_device_signature, DEVICE_SECRET_KEY
    
    # Mock request with query parameters
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/api/v1/notes"
    request.url.query = "user_id=123"
    
    timestamp = str(int(time.time()))
    message = f"GET/api/v1/notesuser_id=123{timestamp}".encode()
    
    signature = hmac.new(
        DEVICE_SECRET_KEY.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    request.headers = {
        "X-Device-Signature": signature,
        "X-Device-Timestamp": timestamp
    }
    
    # Should pass
    assert await verify_device_signature(request) is True
    
    # Test failure with tampered query
    request.url.query = "user_id=456"
    with pytest.raises(HTTPException) as exc:
        await verify_device_signature(request)
    assert exc.value.status_code == 401

# 2. Test Note Ownership
def test_note_ownership_bola():
    from app.utils.security import verify_note_ownership
    
    db = MagicMock()
    note = MagicMock()
    note.id = "note_1"
    note.user_id = "user_1"
    
    # Mock the query chain: db.query(models.Note).filter(id=..., user_id=...).first()
    db.query.return_value.filter.return_value.first.return_value = note
    
    # Also handle the is_admin check which expects a Session but gets a user object in some helpers
    note.is_admin = False
    
    mock_user = MagicMock()
    mock_user.id = "user_1"
    mock_user.is_admin = False
    
    result = verify_note_ownership(db, mock_user, "note_1")
    assert result == note
    
    # User mismatch
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        verify_note_ownership(db, mock_user, "note_1")
    assert exc.value.status_code == 404

# 3. Test NoteStatus State Machine
def test_note_status_processing():
    from app.db.models import NoteStatus
    
    assert NoteStatus.PROCESSING.name == "PROCESSING"

# 4. Test Meeting ROI Logic
def test_dynamic_meeting_roi():
    from app.services.analytics_service import AnalyticsService
    
    db = MagicMock()
    # Mock total_tasks and completed_tasks counts
    db.query.return_value.filter.return_value.count.return_value = 1
    
    # Mock user and usage_stats to avoid MagicMock comparison error
    user = MagicMock()
    user.usage_stats = {"last_analytics_refresh": int(time.time() * 1000)}
    db.query.return_value.filter.return_value.first.return_value = user
    
    note1 = MagicMock()
    note1.transcript_groq = "Hello world " * 200  # 400 words
    note1.title = "Test"
    note1.summary = "Test"
    note1.transcript_deepgram = None
    note1.transcript_android = None
    
    note2 = MagicMock()
    note2.transcript_groq = "Testing ROI " * 100  # 200 words
    note2.title = "Test"
    note2.summary = "Test"
    note2.transcript_deepgram = None
    note2.transcript_android = None
    
    # Mock the notes query: .order_by(...).limit(...).all()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [note1, note2]
    
    # total_words = 600
    # roi = 600 / (40 * 60) = 0.25 hours
    # round(0.25, 1) in Python 3 is 0.2
    
    result = AnalyticsService.get_productivity_pulse(db, "user_1", force_refresh=True)
    assert result["meeting_roi_hours"] == 0.2

# 5. Test Stop-words Expansion
def test_stop_words_filtering():
    from app.services.analytics_service import AnalyticsService
    
    db = MagicMock()
    db.query.return_value.filter.return_value.count.return_value = 1
    
    # Mock user and usage_stats
    user = MagicMock()
    user.usage_stats = {"last_analytics_refresh": int(time.time() * 1000)}
    db.query.return_value.filter.return_value.first.return_value = user
    
    note = MagicMock()
    note.title = "Summary Update"
    note.summary = "This secondary project should include primary tasks"
    note.transcript_groq = ""
    note.transcript_deepgram = None
    note.transcript_android = None
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [note]
    
    result = AnalyticsService.get_productivity_pulse(db, "user_1", force_refresh=True)
    # Topics should return list of dicts
    topics = [item["topic"] for item in result["topic_heatmap"]]
    
    # 'primary' and 'secondary' are in stop_words
    assert "primary" not in topics
    assert "secondary" not in topics
    assert "update" in topics or "include" in topics or "summary" in topics

if __name__ == "__main__":
    pytest.main([__file__])
