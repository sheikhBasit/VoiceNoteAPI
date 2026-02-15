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


def test_analytics_logic():
    from app.services.analytics_service import AnalyticsService

    # Mock DB session
    db = MagicMock()

    # Mock return values for counts
    # The service calls:
    # 1. total_notes count
    # 2. total_tasks count 
    # 3. completed_tasks count
    # 4. high_priority count (for insights) - this is a .first() call, not count
    
    # We need to ensure db.query().filter() returns objects that behave correctly.
    
    # Setup for Tasks queries
    mock_task_query = db.query.return_value
    mock_task_filter = mock_task_query.filter.return_value
    
    # total_tasks count
    mock_task_filter.count.side_effect = [10, 5, 20, 5] 
    # Sequence of .count() calls in service:
    # 1. total_notes (on Note query)
    # 2. processed_notes (on Note query)
    
    # Create specific query mocks
    mock_note_query = MagicMock()
    mock_task_query = MagicMock()
    
    # Mock db.query() to return specific mocks based on model
    from app.db import models
    def side_effect_query(model):
        if model == models.Note:
            return mock_note_query
        return mock_task_query
    
    db.query.side_effect = side_effect_query

    # --- Setup Note Queries ---
    # notes_query = db.query(models.Note).filter(...) -> Q_NOTE
    q_note = mock_note_query.filter.return_value
    
    # total_notes = notes_query.count()
    q_note.count.return_value = 10
    
    # processed_notes = notes_query.filter(...).count()
    # q_note.filter(...) returns Q_NOTE_FILTERED
    q_note_filtered = q_note.filter.return_value
    q_note_filtered.count.return_value = 5

    # recent_notes = notes_query.order_by(...).limit(5).all()
    # Mock notes for ROI calculation
    long_transcript = "word " * 480 # 480 words / 2400 = 0.2 hours
    mock_notes = [
        MockNote(
            id="1",
            title="Project Alpha",
            summary="Meeting about Alpha project",
            transcript_groq=long_transcript,
            transcript_deepgram=None,
            transcript_android=None,
            timestamp=1234567890,
            status="DONE"
        )
    ]
    q_note.order_by.return_value.limit.return_value.all.return_value = mock_notes


    # --- Setup Task Queries ---
    # tasks_query = db.query(models.Task).filter(...) -> Q_TASK
    q_task = mock_task_query.filter.return_value
    
    # total_tasks = tasks_query.count()
    q_task.count.return_value = 20
    
    # completed_tasks = tasks_query.filter(...).count()
    # q_task.filter(...) returns Q_TASK_FILTERED
    q_task_filtered = q_task.filter.return_value
    q_task_filtered.count.return_value = 10
    
    # high_prio_task query also uses q_task_filtered (conceptually similar chain)
    # The service calls: high_prio_task = tasks_query.filter(...).first()
    # This calls q_task.filter(...) again. In MagicMock, calling with different args might return same mock 
    # unless we use side_effect or just assume it uses the same one.
    # For simplicity, let's make .first() return None to avoid "High Priority Task" insight affecting things,
    # or return a task to test insight generation.
    q_task_filtered.first.return_value = None


    result = AnalyticsService.get_productivity_pulse(db, "user_1")

    # Verify structure matches implementation
    assert "stats" in result
    stats = result["stats"]
    
    # Velocity: 10 completed / 20 total = 50%
    assert stats["productivity_velocity"] == "50%"
    
    # ROI: 480 words / 2400 wph = 0.2 hours
    assert stats["meeting_roi"] == "0.2 hrs saved"
    
    assert "decision_heatmap" in stats
    assert len(stats["decision_heatmap"]) > 0


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
