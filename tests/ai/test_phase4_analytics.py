import pytest
from unittest.mock import patch, MagicMock
from app.services.analytics_service import AnalyticsService
from app.db import models

@pytest.mark.asyncio
async def test_team_metrics_calculation(db_session):
    # 1. Setup data
    team_id = "test_team_1"
    user = models.User(id="user_1", email="user1@test.com", name="User One")
    db_session.add(user)
    
    # 3 notes
    for i in range(3):
        n = models.Note(id=f"n_{i}", user_id="user_1", team_id=team_id, title=f"Note {i}")
        db_session.add(n)
        
    # 2 tasks (1 done)
    t1 = models.Task(id="t1", user_id="user_1", team_id=team_id, is_done=True, priority=models.Priority.LOW)
    t2 = models.Task(id="t2", user_id="user_1", team_id=team_id, is_done=False, priority=models.Priority.HIGH)
    db_session.add_all([t1, t2])
    db_session.commit()
    
    # 2. Test metrics
    metrics = AnalyticsService.get_team_metrics(db_session, team_id)
    assert metrics["total_notes"] == 3
    assert metrics["total_tasks"] == 2
    assert metrics["completed_tasks"] == 1
    assert metrics["high_priority_pending"] == 1
    assert metrics["completion_rate"] == 50.0

@pytest.mark.asyncio
async def test_team_analytics_endpoint(client, db_session):
    # 1. Setup user and team
    user = models.User(id="user_a", email="a@test.com", name="A User")
    team = models.Team(id="team_a", name="Team A", owner_id="user_a")
    team.members.append(user)
    db_session.add_all([user, team])
    db_session.commit()
    
    # 2. Dependency override for auth
    from app.main import app
    from app.api.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user
    
    try:
        with patch("app.services.analytics_service.AnalyticsService.generate_team_progress_summary", return_value="Great progress!"):
            response = client.get(f"/api/v1/teams/{team.id}/analytics")
            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data
            assert data["ai_summary"] == "Great progress!"
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_lead_extraction_persistence(db_session):
    # This test verifies that if LLM returns business_leads, they are stored
    from app.services.ai_service import NoteAIOutput
    
    mock_analysis = NoteAIOutput(
        title="Sales Call",
        summary="Met with Acme Corp",
        priority=models.Priority.HIGH,
        transcript="...",
        business_leads=[
            {
                "name": "Acme Corp",
                "prospect_type": "CLIENT",
                "context": "Interested in bulk order",
                "contact_info": "sales@acme.com"
            }
        ]
    )
    
    # Mock worker persistence logic simplified
    note = models.Note(id="note_lead", user_id="u1", title="Old Title")
    db_session.add(note)
    db_session.commit()
    
    # Simulate update in worker
    note.semantic_analysis = {"business_leads": mock_analysis.business_leads}
    db_session.commit()
    
    # Re-fetch and verify
    updated_note = db_session.query(models.Note).filter(models.Note.id == "note_lead").first()
    assert "business_leads" in updated_note.semantic_analysis
    assert updated_note.semantic_analysis["business_leads"][0]["name"] == "Acme Corp"
