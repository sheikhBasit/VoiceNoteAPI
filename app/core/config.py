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
    
    # Validation
    MAX_TRANSCRIPT_LENGTH: int = 100000
    AUDIO_BITRATE_THRESHOLD: int = 128000
    
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