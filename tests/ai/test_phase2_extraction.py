import pytest
import os
import json
from unittest.mock import patch, MagicMock, PropertyMock
from app.services.ai_service import AIService
from app.schemas.note import NoteAIOutput

@pytest.fixture(autouse=True)
def setup_groq_env():
    os.environ["GROQ_API_KEY"] = "mock_key"
    yield
    if "GROQ_API_KEY" in os.environ:
        del os.environ["GROQ_API_KEY"]

@pytest.mark.asyncio
async def test_llm_brain_extraction_with_entities_and_actions():
    """Test AIService.llm_brain_sync extracts assigned_entities and actions correctly."""
    service = AIService()
    
    # Mock dynamic settings
    service._get_dynamic_settings = MagicMock(return_value={
        "llm_model": "llama-3.1-8b-instant",
        "temperature": 0.3,
        "max_tokens": 4096,
        "top_p": 0.9
    })
    
    # Sample Mocked Response from LLM
    mock_content = {
        "title": "Meeting with John",
        "summary": "Discussed the website project and assigned tasks.",
        "priority": "HIGH",
        "tags": ["Business", "Web"],
        "assigned_entities": [
            {"name": "John Doe", "email": "john@example.com"}
        ],
        "tasks": [
            {
                "title": "Call John",
                "description": "Call John to discuss the project",
                "priority": "HIGH",
                "deadline": "2026-02-15",
                "assigned_entities": [{"name": "John Doe", "phone": "1234567890"}],
                "actions": {
                    "call": {"phone": "1234567890", "name": "John Doe"}
                }
            }
        ]
    }
    
    # Setting up the mock response structure
    mock_message = MagicMock()
    mock_message.content = json.dumps(mock_content)
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    # Patch the singleton client to ensure it's picked up
    with patch("app.services.ai_service.AIService.groq_client", new_callable=PropertyMock) as mock_client_prop:
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response
        
        # Execute extraction
        transcript = "I need to call John Doe at 1234567890 tomorrow about the website."
        result = service.llm_brain_sync(transcript, user_role="DEVELOPER")
        
        # Verify results
        assert isinstance(result, NoteAIOutput)
        assert result.title == "Meeting with John"
        assert len(result.assigned_entities) == 1
        assert result.assigned_entities[0]["name"] == "John Doe"
        
        assert len(result.tasks) == 1
        task = result.tasks[0]
        assert task["title"] == "Call John"
        assert len(task["assigned_entities"]) == 1
        assert task["assigned_entities"][0]["phone"] == "1234567890"
        assert "call" in task["actions"]
        assert task["actions"]["call"]["phone"] == "1234567890"

@pytest.mark.asyncio
async def test_llm_brain_extraction_with_whatsapp_and_maps():
    """Test extraction of WhatsApp and Map actions."""
    service = AIService()
    service._get_dynamic_settings = MagicMock(return_value={"llm_model": "test", "temperature": 0.3, "max_tokens": 10, "top_p": 0.9})
    
    mock_content = {
        "title": "Grocery Trip",
        "summary": "Need to go to the store.",
        "priority": "MEDIUM",
        "tasks": [
            {
                "title": "Buy Milk",
                "description": "Go to Whole Foods and buy milk",
                "actions": {
                    "map": {"location": "Whole Foods", "query": "Whole Foods near me"},
                    "whatsapp": {"phone": "9876543210", "message": "I am buying milk"}
                }
            }
        ]
    }
    
    mock_message = MagicMock()
    mock_message.content = json.dumps(mock_content)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]

    with patch("app.services.ai_service.AIService.groq_client", new_callable=PropertyMock) as mock_client_prop:
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response
        
        result = service.llm_brain_sync("Go to Whole Foods and text mom I am buying milk.", user_role="GENERIC")
        
        assert len(result.tasks) == 1
        actions = result.tasks[0]["actions"]
        assert "map" in actions
        assert "whatsapp" in actions
        assert actions["map"]["location"] == "Whole Foods"
        assert actions["whatsapp"]["phone"] == "9876543210"
