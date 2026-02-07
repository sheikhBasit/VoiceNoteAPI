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
    - title: Catchy, relevant title for the whole note (max 10 words).
    - summary: 2-3 sentence concise summary explaining the core value.
    - priority: "HIGH", "MEDIUM", or "LOW" based on urgency.
    - tags: List of 2-4 strings (categories like "Business", "Personal", "Shopping", "Idea").
    - tasks: List of objects:
        - title: A very short, punchy title for the task (e.g. "Email John").
        - description: A detailed description of exactly what needs to be done.
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
    
    TASK ACTION DETECTION (PROACTIVE & AGGRESSIVE):
    For each task, proactively detect if it requires specific actions. 
    
    1. GOOGLE SEARCH: Generate if the task involves research, investigation, finding info, or could benefit from external guides.
       - Extract: {"google_search": {"query": "search terms"}}
       
    2. MAP: If task mentions a specific place, address, store, or "go to X", "at X".
       - Extract: {"map": {"location": "Place Name", "query": "Store or Address near town"}}

    3. EMAIL: If task mentions sending email, emailing someone, or contacting via email.
       - Extract: {"email": {"to": "email@example.com", "name": "Person Name", "subject": "...", "body": "..."}}
       
    4. WHATSAPP: If task mentions WhatsApp, messaging, texting, or sending message.
       - Extract: {"whatsapp": {"phone": "+1234567890", "name": "Contact Name", "message": "..."}}
       
    5. AI ASSISTANCE (LLM PROMPT): If task needs ChatGPT/Gemini/Claude help or asks to "ask AI". Always provide a helpful starting prompt.
       - Extract: {"ai_prompt": {"model": "gemini|chatgpt|claude|gpt-4", "prompt": "Specialized query", "context": "relevant context"}}
    
    EXAMPLE OUTPUT:
    {
      "title": "Grocery & Planning",
      "summary": "Need to buy milk and research new personal growth strategies.",
      "priority": "MEDIUM",
      "tags": ["Shopping", "Self Improvement", "Planning"],
      "tasks": [
        {
          "title": "Buy Milk",
          "description": "Stop at the grocery store to buy organic milk.",
          "priority": "MEDIUM",
          "due_date": null,
          "actions": {
            "map": {"location": "Grocery Store", "query": "Grocery stores nearby"}
          }
        },
        {
          "title": "Self Reflection",
          "description": "Sit down and ask questions about current achievements and improvements.",
          "priority": "LOW",
          "due_date": null,
          "actions": {
            "google_search": {"query": "effective self reflection questions for personal growth"},
            "ai_prompt": {"model": "gpt-4", "prompt": "Provide 10 deep self-reflection questions for personal achievements"}
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