from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class AISettingsBase(BaseModel):
    llm_model: str = "llama-3.1-70b-versatile"
    llm_fast_model: str = "llama-3.1-8b-instant"
    temperature: int = Field(3, ge=0, le=10)
    max_tokens: int = Field(4096, ge=1, le=32768)
    top_p: int = Field(9, ge=0, le=10)
    stt_engine: str = "deepgram"
    groq_whisper_model: str = "whisper-large-v3-turbo"
    deepgram_model: str = "nova-3"
    semantic_analysis_prompt: Optional[str] = None

class AISettingsUpdate(AISettingsBase):
    pass

class AISettingsResponse(AISettingsBase):
    updated_at: int
    updated_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
