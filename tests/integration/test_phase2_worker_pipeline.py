import pytest
import json
from unittest.mock import patch, MagicMock, PropertyMock
from app.worker.task import note_process_pipeline
from app.db import models
from app.schemas.note import NoteAIOutput

@pytest.mark.asyncio
async def test_worker_pipeline_persists_entities_and_actions(db_session):
    """Integration test for the full note processing pipeline."""
    # 1. Create a test user and note
    user = models.User(id="user_123", email="test@example.com", name="Test User", password_hash="...")
    db_session.add(user)
    db_session.commit()
    
    note = models.Note(
        id="note_123",
        user_id="user_123",
        title="Original Title",
        summary="Original Summary",
        transcript_groq="I need to call John at 1234567890 tomorrow."
    )
    db_session.add(note)
    db_session.commit()
    
    # 2. Mock AIService to return structured Phase 2 data
    mock_ai_output = NoteAIOutput(
        title="Processed Title",
        summary="Processed Summary",
        priority="HIGH",
        transcript="I need to call John at 1234567890 tomorrow.",
        tasks=[
            {
                "title": "Call John",
                "description": "Call John at 1234567890",
                "priority": "HIGH",
                "deadline": "2026-02-15",
                "assigned_entities": [{"name": "John", "phone": "1234567890"}],
                "actions": {
                    "call": {"phone": "1234567890", "name": "John"}
                }
            }
        ],
        tags=["Urgent"],
        assigned_entities=[{"name": "John", "phone": "1234567890"}],
        metadata={"all_transcripts": {"groq": "Transcription", "deepgram": "Transcription"}}
    )
    
    with patch("app.services.ai_service.AIService.llm_brain_sync", return_value=mock_ai_output), \
         patch("app.services.ai_service.AIService.generate_embedding_sync", return_value="[0.1, 0.2]"), \
         patch("app.worker.task.broadcast_user_update") as mock_user_broadcast, \
         patch("app.worker.task.broadcast_team_update") as mock_team_broadcast, \
         patch("app.worker.task.preprocess_audio_pipeline", return_value="uploads/test_refined.wav"), \
         patch("app.worker.task.requests.get") as mock_get, \
         patch("app.services.ai_service.AIService.transcribe_with_failover_sync", return_value=("Transcript", "nova", ["en"], {"groq": "Transcript"})), \
         patch("os.path.exists", return_value=True), \
         patch("os.path.getsize", return_value=1024), \
         patch("os.remove", return_value=None):
        
        # 3. Run the pipeline
        note_process_pipeline("note_123", local_file_path="uploads/test.wav", user_role="DEVELOPER")
        
        # 4. Verify Database state
        db_session.refresh(note)
        assert note.title == "Processed Title"
        
        tasks = db_session.query(models.Task).filter(models.Task.note_id == "note_123").all()
        assert len(tasks) == 1
        task = tasks[0]
        
        assert task.title == "Call John"
        assert task.priority == models.Priority.HIGH
        
        # Verify suggested_actions (hydrated by ActionSuggestionService in worker)
        assert "call" in task.suggested_actions
        assert task.suggested_actions["call"]["deeplink"] == "tel:1234567890"
        
        # Verify assigned_entities (passed through to Task model)
        assert len(task.assigned_entities) == 1
        assert task.assigned_entities[0]["name"] == "John"
        assert task.assigned_entities[0]["phone"] == "1234567890"
