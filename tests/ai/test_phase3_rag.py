import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from app.services.rag_service import RAGService
from app.db import models
from app.services.ai_service import AIService

@pytest.mark.asyncio
async def test_rag_find_similar_notes(db_session):
    # 1. Setup mock data
    user = models.User(id="user_rag", email="rag@example.com", name="RAG User")
    db_session.add(user)
    db_session.commit()
    
    note1 = models.Note(
        id="note_1",
        user_id="user_rag",
        title="Project Apollo",
        summary="A project about space exploration.",
        embedding="[0.1, 0.2, 0.3]"  # Mock vector as string
    )
    note2 = models.Note(
        id="note_2",
        user_id="user_rag",
        title="Cooking Pasta",
        summary="How to make the best carbonara.",
        embedding="[0.9, 0.8, 0.7]"
    )
    db_session.add_all([note1, note2])
    db_session.commit()
    
    # 2. Test find_similar_notes
    with patch("sqlalchemy.orm.query.Query.all", return_value=[note1]):
        results = RAGService.find_similar_notes(db_session, "user_rag", [0.11, 0.21, 0.31])
        assert len(results) == 1
        assert results[0].title == "Project Apollo"

def test_rag_format_context():
    note = MagicMock(spec=models.Note)
    note.title = "Test Note"
    note.summary = "Test Summary"
    note.transcript = "Test Transcript content"
    
    context = RAGService.format_context_for_llm([note])
    assert "--- HISTORICAL CONTEXT" in context
    assert "Test Note" in context
    assert "Test Summary" in context

@pytest.mark.asyncio
async def test_semantic_search_endpoint(client, db_session):
    # 1. Setup user
    user = models.User(id="user_search", email="search@example.com", name="Search User")
    db_session.add(user)
    db_session.commit()
    
    # 2. Setup dependency overrides for auth
    from app.main import app
    from app.api.dependencies import get_current_user
    
    app.dependency_overrides[get_current_user] = lambda: user
    
    try:
        with patch("app.services.ai_service.AIService.generate_embedding_sync", return_value=[0.1]*384), \
             patch("app.services.rag_service.RAGService.find_similar_notes", return_value=[]):
            
            response = client.post(
                "/api/v1/ai/search",
                json={"query": "space exploration", "limit": 5}
            )
            assert response.status_code == 200
            assert isinstance(response.json(), list)
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_ai_ask_endpoint(client, db_session):
    # 1. Setup user
    user = models.User(id="user_ask", email="ask@example.com", name="Ask User")
    db_session.add(user)
    db_session.commit()
    
    # 2. Setup dependency overrides
    from app.main import app
    from app.api.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user
    
    try:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "This is a RAG-based answer."
        
        with patch("app.services.rag_service.RAGService.get_context_for_transcript", return_value="Some context"), \
             patch("app.services.ai_service.AIService.groq_client", new_callable=PropertyMock) as mock_groq_p:
            
            mock_client = MagicMock()
            mock_groq_p.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response
            
            response = client.post(
                "/api/v1/ai/ask",
                json={"question": "What is my project about?"}
            )
            assert response.status_code == 200
            assert response.json()["answer"] == "This is a RAG-based answer."
    finally:
        app.dependency_overrides.clear()
