import pytest
import shutil
import os
import uuid
from unittest.mock import MagicMock, patch
from app.worker.task import process_voice_note_pipeline
from app.db.models import Note, NoteStatus, User, UserRole
from app.services.ai_service import AIService
from app.core.audio import preprocess_audio_pipeline

# Mock constants
TEST_AUDIO_SOURCE = "/home/basitdev/Me/StudioProjects/VoiceNoteAPI/tests/assets/ideal_quality.wav"

@pytest.fixture
def mock_db():
    mock = MagicMock()
    # Mock return values for common queries
    mock.query().filter().update.return_value = 1
    mock.query().filter().scalar.return_value = "test_user_001"
    
    # Mock Note object
    mock_note = Note(
        id="test_note_id",
        user_id="test_user_001",
        status=NoteStatus.PENDING,
        raw_audio_url=None
    )
    mock.query().filter().first.return_value = mock_note
    return mock

@pytest.fixture
def mock_ai_service():
    with patch("app.worker.task.AIService") as mock:
        instance = mock.return_value
        instance.run_full_analysis_sync.return_value = MagicMock(
            title="Pro Agent Integration Test",
            summary="A deep test of the Pro Agent pipeline.",
            transcript="This is a test transcript for the Pro Agent pipeline.",
            tasks=[{"description": "Verify the pipeline works", "priority": "HIGH", "deadline": None}]
        )
        instance.generate_embedding_sync.return_value = [0.1] * 384
        yield instance

@patch("app.worker.task.SessionLocal")
@patch("app.worker.task.broadcast_ws_update")
def test_pro_agent_pipeline_e2e(mock_ws, mock_session_local, mock_ai_service, mock_db):
    """
    Verifies the full Pro Agent backend pipeline:
    Preprocessing -> STT -> Analysis -> DB Save
    """
    mock_session_local.return_value = mock_db
    
    # Setup test file
    note_id = f"integration_test_{uuid.uuid4()}"
    temp_upload = f"uploads/{note_id}.wav"
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    shutil.copy(TEST_AUDIO_SOURCE, temp_upload)
    
    user_role = "GENERIC"
    
    try:
        # Execute pipeline
        result = process_voice_note_pipeline(note_id, temp_upload, user_role)
        
        # Assertions
        assert result["status"] == "success"
        assert result["note_id"] == note_id
        
        # Verify DB updates
        assert mock_db.commit.called
        
        # Verify audio refinement happened
        refined_path = temp_upload.replace(".wav", "_refined.wav")
        assert os.path.exists(refined_path), "Refined audio file was not created"
        
        print(f"\n✅ Integration Test Passed: {note_id}")
        
    finally:
        # Cleanup
        if os.path.exists(temp_upload):
            os.remove(temp_upload)
        refined_path = temp_upload.replace(".wav", "_refined.wav")
        if os.path.exists(refined_path):
            os.remove(refined_path)

if __name__ == "__main__":
    # Allow running standalone
    pytest.main([__file__, "-s"])
