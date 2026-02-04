from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from typing import List

class AISettings(BaseSettings):
    """
    Centralized AI and System configurations.
    Validation is handled by Pydantic.
    """
    # LLM Parameters
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_FAST_MODEL: str = "llama-3.1-8b-instant"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    TEMPERATURE: float = 0.3
    MAX_TOKENS: int = 4096
    TOP_P: float = 0.9
    
    # STT Models
    GROQ_WHISPER_MODEL: str = "whisper-large-v3-turbo"
    DEEPGRAM_MODEL: str = "nova-3"
    
    # Validation
    MAX_TRANSCRIPT_LENGTH: int = 100000
    AUDIO_BITRATE_THRESHOLD: int = 128000
    SHORT_AUDIO_THRESHOLD_SEC: int = 45 # Audio below this goes to 'short' queue
    SHORT_AUDIO_THRESHOLD_SEC: int = 45 # Audio below this goes to 'short' queue
    
    # --- STORAGE SETTINGS (NEW) ---
    MINIO_ENDPOINT: str = Field(default="minio:9000", validation_alias="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin", validation_alias="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(default="minioadminpassword", validation_alias="MINIO_SECRET_KEY")
    MINIO_BUCKET_NAME: str = Field(default="incoming", validation_alias="MINIO_BUCKET_NAME")
    MINIO_SECURE: bool = Field(default=False, validation_alias="MINIO_SECURE")
    
    # --- COMMERCIAL SETTINGS (NEW) ---
    STRIPE_SECRET_KEY: str = Field(default="sk_test_placeholder", validation_alias="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field(default="whsec_placeholder", validation_alias="STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID_PRO: str = Field(default="price_placeholder", validation_alias="STRIPE_PRICE_ID_PRO")
    
    RECALL_AI_API_KEY: str = Field(default="", validation_alias="RECALL_AI_API_KEY")
    DAILY_CO_API_KEY: str = Field(default="", validation_alias="DAILY_CO_API_KEY")
    
    GOOGLE_CLIENT_ID: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", validation_alias="GOOGLE_CLIENT_SECRET")
    
    # AI Prompts
    EXTRACTION_SYSTEM_PROMPT: str = """
    You are an advanced AI Note-Taker. Your goal is to convert messy meeting or lecture transcripts into structured insights.
    Analyze the transcription and return a structured JSON object.
    
    OUTPUT JSON FORMAT (STRICT):
    - title: Catchy, relevant title (max 10 words).
    - summary: 2-3 sentence concise summary explaining the core value.
    - priority: "HIGH", "MEDIUM", or "LOW" based on urgency.
    - tasks: List of objects:
        - title: The specific action item.
        - priority: "HIGH", "MEDIUM", or "LOW".
        - due_date: ISO 8601 format (YYYY-MM-DD) if mentioned, else null.
        - actions: Object with detected action types (optional)
    
    PRIORITY ASSIGNMENT GUIDELINES (CRITICAL):
    When temporal context is provided (note creation time, current time, user timezone):
    - Tasks with "today", "now", "urgent", "ASAP", or deadlines within 24-48 hours → HIGH priority
    - Tasks with deadlines within 1 week → MEDIUM priority
    - Tasks with vague deadlines ("someday", "eventually", "when I have time") → LOW priority
    - Consider the time gap between note creation and current time for context
    - Use user's local timezone to understand "today", "tomorrow", "this week" correctly
    
    When no temporal context is provided, use semantic urgency cues from the transcript.
    
    TASK ACTION DETECTION (CRITICAL):
    For each task, detect if it requires specific actions and extract metadata:
    
    1. GOOGLE SEARCH: If task involves research, investigation, looking up, or mentions "google/search"
       - Extract: {"google_search": {"query": "search terms"}}
       
    2. EMAIL: If task mentions sending email, emailing someone, or contacting via email
       - Extract: {"email": {"to": "email@example.com", "name": "Person Name", "subject": "...", "body": "..."}}
       
    3. WHATSAPP: If task mentions WhatsApp, messaging, texting, or sending message
       - Extract: {"whatsapp": {"phone": "+1234567890", "name": "Contact Name", "message": "..."}}
       
    4. AI ASSISTANCE: If task needs ChatGPT/Gemini/Claude help or asks to "ask AI"
       - Extract: {"ai_prompt": {"model": "gemini|chatgpt|claude", "context": "relevant context"}}
    
    EXAMPLE OUTPUT:
    {
      "title": "Project Planning Meeting",
      "summary": "Discussed Q1 goals and assigned research tasks.",
      "priority": "HIGH",
      "tasks": [
        {
          "title": "Research competitor pricing strategies",
          "priority": "HIGH",
          "due_date": "2026-02-05",
          "actions": {
            "google_search": {"query": "competitor pricing strategies 2026"}
          }
        },
        {
          "title": "Email John about budget approval",
          "priority": "MEDIUM",
          "due_date": null,
          "actions": {
            "email": {
              "to": "john@company.com",
              "name": "John",
              "subject": "Budget Approval Request",
              "body": "Hi John,\\n\\nFollowing up on our meeting regarding the Q1 budget..."
            }
          }
        }
      ]
    }
    """

    CONFLICT_DETECTOR_PROMPT: str = """
    Role: CONFLICT_DETECTOR
    Task: Identify any contradictions between the NEW SUMMARY and the EXISTING NOTES.
    
    NEW SUMMARY:
    {new_summary}
    
    EXISTING NOTES:
    {existing_notes}
    
    Return a JSON list of conflicts:
    [
        {{"fact": "statement A", "conflict": "statement B", "explanation": "why they conflict", "severity": "HIGH/MEDIUM"}}
    ]
    If no conflicts, return empty list [].
    """

    RAG_SYNTHESIS_PROMPT: str = """
    User Query: {query}
    
    Using the provided context (local notes and web search results), please answer the user's question.
    - If the information is from their local notes, mention it.
    - If the information is from the web because notes were insufficient, clarify that.
    - Be concise and professional.
    
    CONTEXT:
    {context}
    """

    TRUSTED_HOSTS: List[str] = ["*"]
    # Tell Pydantic to read from .env
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_ai_settings():
    """
    Returns a cached instance of the settings to avoid
    repeatedly reading the .env file from disk.
    """
    return AISettings()
    
ai_config = get_ai_settings()