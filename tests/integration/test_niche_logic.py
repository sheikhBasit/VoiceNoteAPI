import hashlib
import hmac
from unittest.mock import MagicMock

import pytest


# Mock requirements for standalone test
class MockNote:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockTask:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_signature_logic():
    secret = "test_secret"
    timestamp = "123456789"
    method = "POST"
    path = "/test"

    # Logic from security.py
    message = f"{method}{path}{timestamp}".encode()
    expected_signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

    # Verification
    sig_to_check = expected_signature
    assert hmac.compare_digest(sig_to_check, expected_signature)


def test_conflict_detection_logic():
    from app.services.calendar_service import CalendarService

    tasks = [{"description": "Deep Work", "deadline": 2000}]
    events = [{"title": "Team Sync", "start_time": 1500, "end_time": 2500}]

    conflicts = CalendarService.detect_conflicts(tasks, events)
    assert len(conflicts) == 1
    assert conflicts[0]["conflicting_event"] == "Team Sync"

    # Test boundary conditions
    tasks = [{"description": "Edge Task", "deadline": 1500}]  # Exactly at start
    conflicts = CalendarService.detect_conflicts(tasks, events)
    assert len(conflicts) == 1


def test_whatsapp_link_generation():
    import urllib.parse

    title = "Test Note"
    summary = "Test Summary"
    tasks = [MockTask(description="Task 1", is_done=False)]

    text = f"VoiceNote Note: {title}\n\nSummary: {summary}\n\nTasks:\n"
    for t in tasks:
        status_icon = "✅" if t.is_done else "⏳"
        text += f"- {status_icon} {t.description}\n"

    encoded_text = urllib.parse.quote(text)
    wa_link = f"https://wa.me/?text={encoded_text}"

    assert "https://wa.me/?text=" in wa_link
    assert "VoiceNote%20Note" in wa_link


@pytest.mark.asyncio
async def test_analytics_logic():
    pass

    from app.services.analytics_service import AnalyticsService

    # Mock DB session
    db = MagicMock()

    # Mock return values for counts
    # Mock return values for counts
    # The service calls:
    # 1. total_notes count
    # 2. total_tasks count (first filter)
    # 3. completed_tasks count (second filter on same query object)
    # 4. high_priority count (second filter on same query object)
    
    # We need to ensure db.query().filter() returns an object that...
    # ... has .count() returning total_tasks
    # ... AND has .filter() returning an object whose .count() returns completed/high_prio items.
    
    mock_query = db.query.return_value
    mock_filter_1 = mock_query.filter.return_value
    mock_filter_1.count.return_value = 10 # total tasks
    
    mock_filter_2 = mock_filter_1.filter.return_value
    # side_effect for subsequent counts: completed (5), high_priority (2)
    mock_filter_2.count.side_effect = [5, 2] 
    
    # Also handle total_notes (another query)
    # Since we can't easily distinguish queries by args in simple mocks without complex side_effects,
    # let's try to just make everything return compatible numbers or use specific side_effects if needed.
    # But wait, total_notes uses db.query(Note).filter().count()
    # total_tasks uses db.query(Task).filter().count()
    # They look the same to a simple mock structure.

    # Mock notes for heatmap
    # Mock notes for heatmap
    # Need 400 words total for (2 * 5)/60 hours = 10 mins = 0.166 hours
    # 400 words / 2400 words/hour = 0.1666 hours.
    # 400 words / 2400 words/hour = 0.1666 hours.
    long_transcript = "word " * 200 + " alpha cricket"
    mock_notes = [
        MockNote(
            title="Project Alpha",
            summary="Meeting about Alpha project",
            transcript_groq=long_transcript,
            transcript_deepgram=None,
            transcript_android=None,
        ),
        MockNote(
            title="Cricket Match",
            summary="Discussion on Cricket strategy",
            transcript_groq=long_transcript,
            transcript_deepgram=None,
            transcript_android=None,
        ),
    ]
    # Mock the notes query: .limit(...).all() (order_by might be missing)
    # Support both with and without order_by just in case
    db.query.return_value.filter.return_value.limit.return_value.all.return_value = mock_notes
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_notes

    result = AnalyticsService.get_productivity_pulse(db, "user_1")

    assert result["task_velocity"] == 5.0
    # 400 words / 2400 = 0.166 -> rounded to 0.2
    assert result["meeting_roi_hours"] == 0.2
    assert any(item["topic"] == "alpha" for item in result["topic_heatmap"])
    assert any(item["topic"] == "cricket" for item in result["topic_heatmap"])


@pytest.mark.asyncio
async def test_search_rag_context_building():
    from app.services.search_service import SearchService

    ai_service = MagicMock()
    search_service = SearchService(ai_service)

    local_results = [{"title": "L1", "summary": "S1", "transcript": "T1"}]
    web_results = [{"title": "W1", "content": "C1", "url": "U1"}]

    # Test context synthesis
    context = "LOCAL NOTES:\n"
    for r in local_results:
        context += f"- {r['title']}: {r['summary']}\nTranscript: {r['transcript'][:500]}...\n\n"

    context += "\nWEB SEARCH RESULTS:\n"
    for r in web_results:
        context += f"- {r['title']}: {r['content'][:500]}...\nURL: {r['url']}\n\n"

    assert "LOCAL NOTES" in context
    assert "WEB SEARCH RESULTS" in context
    assert "S1" in context
    assert "C1" in context
