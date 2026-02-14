import pytest
from app.services.action_suggestion_service import ActionSuggestionService

def test_generate_google_search():
    result = ActionSuggestionService.generate_google_search("python programming")
    assert "python+programming" in result["url"]
    assert result["query"] == "python programming"

def test_generate_email_draft():
    result = ActionSuggestionService.generate_email_draft(
        to="test@example.com",
        name="Test User",
        subject="Hello",
        body="How are you?"
    )
    assert result["to"] == "test@example.com"
    assert "mailto:test@example.com" in result["deeplink"]
    assert "Hello" in result["deeplink"]

def test_generate_whatsapp_message():
    result = ActionSuggestionService.generate_whatsapp_message(
        phone="+1 (234) 567-890",
        message="Hi there!"
    )
    assert result["phone"] == "+1 (234) 567-890"
    assert "1234567890" in result["url"]
    assert "Hi+there%21" in result["url"]
    assert "whatsapp://send?phone=1234567890" in result["deeplink"]

def test_generate_call_link():
    result = ActionSuggestionService.generate_call_link("+1-234-567-890")
    assert result["deeplink"] == "tel:1234567890"

def test_generate_map_link():
    result = ActionSuggestionService.generate_map_link("Eiffel Tower", "Paris")
    assert "google.com/maps" in result["url"]
    assert "Paris" in result["url"]
    assert "geo:0,0?q=Paris" in result["deeplink"]

def test_generate_ai_prompt():
    result = ActionSuggestionService.generate_ai_prompt(
        model="gpt-4",
        task_description="Explain recursion",
        context="Study group note"
    )
    assert result["model"] == "gpt-4"
    assert "Explain recursion" in result["prompt"]
    assert "chat.openai.com" in result["url"]
