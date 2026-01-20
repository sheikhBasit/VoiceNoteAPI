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
    LLM_MODEL: str = "llama-3.1-70b-versatile"
    TEMPERATURE: float = 0.3
    MAX_TOKENS: int = 4096
    TOP_P: float = 0.9  # Adjusted for better diversity in summaries
    
    # STT Models
    GROQ_WHISPER_MODEL: str = "whisper-large-v3-turbo"
    DEEPGRAM_MODEL: str = "nova-3"
    
    # System Instructions
    BASE_SYSTEM_PROMPT: str = """
    You are an intelligent AI Note-Taker. Your goal is to convert messy meeting or lecture transcripts into structured insights.
    
    OUTPUT JSON FORMAT (STRICT):
    - title: Catchy, relevant title.
    - summary: 2-sentence concise summary.
    - priority: "HIGH", "MEDIUM", or "LOW".
    - transcript: Cleaned version with Speaker labels.
    - tasks: List of objects:
        - description: The specific action item.
        - priority: "HIGH", "MEDIUM", or "LOW".
        - deadline: Unix timestamp or null.
        - assigned_contact_name: Name or null.
        - communication_type: "WHATSAPP", "SMS", "CALL", "MEET", or "SLACK".
    """

    TRUSTED_HOSTS: List[str] = ["*"]
    # Tell Pydantic to read from .env
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore" # Prevents errors if extra vars exist in .env
    )

@lru_cache()
def get_ai_settings():
    """
    Returns a cached instance of the settings to avoid
    repeatedly reading the .env file from disk.
    """
    return AISettings()
    
ai_config = get_ai_settings()