import os
import json
import asyncio
import time
import uuid
import logging
import hashlib
from typing import List, Tuple, Optional, Dict, Any
from groq import Groq
from deepgram import DeepgramClient
from pyannote.audio import Pipeline
import torch
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import ai_config
from app.schemas.note import NoteAIOutput
from app.utils.ai_service_utils import (
    retry_with_backoff,
    with_timeout,
    validate_transcript,
    validate_ai_response,
    validate_json_response,
    RequestTracker,
    RateLimiter,
    get_request_tracker,
    AIServiceError
)
from app.db.session import SessionLocal
from app.db import models
from sqlalchemy.orm import Session

logger = logging.getLogger("VoiceNote")

class AIService:
    def __init__(self):
        # AI Clients with graceful environment handling
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None
        
        self.dg_api_key = os.getenv("DEEPGRAM_API_KEY")
        self.dg_client = DeepgramClient() if self.dg_api_key else None
        
        self.request_tracker = get_request_tracker()
        
        # Local model for embeddings (Free alternative to OpenAI)
        self.local_embedding_model = None
        
        # Diarization Pipeline (Optional based on environment)
        self.hf_token = os.getenv("HF_TOKEN")
        self.diarization_pipeline = None
        if self.hf_token and os.getenv("ENABLE_AI_PIPELINES", "false") == "true":
            try:
                self.diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization@2.1",
                    use_auth_token=self.hf_token
                )
            except Exception as e:
                logger.error(f"Failed to load speaker diarization: {e}")

    def _get_local_embedding_model(self):
        if self.local_embedding_model is None:
            try:
                # Using all-MiniLM-L6-v2 which produces 384 dimensions
                logger.info("Loading local embedding model: all-MiniLM-L6-v2")
                self.local_embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                logger.error(f"Failed to load local embedding model: {e}")
        return self.local_embedding_model

    def _get_dynamic_settings(self):
        """Fetches settings from DB with a simple cache."""
        # Check cache (1 min)
        if hasattr(self, "_settings_cache") and (time.time() - self._settings_last_fetch < 60):
            return self._settings_cache
            
        try:
            db = SessionLocal()
            settings = db.query(models.SystemSettings).first()
            if not settings:
                # Initialize default if missing
                settings = models.SystemSettings(id=1)
                db.add(settings)
                db.commit()
                db.refresh(settings)
            
            # Convert to dictionary for easier access
            self._settings_cache = {
                "llm_model": settings.llm_model,
                "llm_fast_model": settings.llm_fast_model,
                "temperature": settings.temperature / 10.0,
                "max_tokens": settings.max_tokens,
                "top_p": settings.top_p / 10.0,
                "stt_engine": settings.stt_engine,
                "groq_whisper_model": settings.groq_whisper_model,
                "deepgram_model": settings.deepgram_model
            }
            self._settings_last_fetch = time.time()
            db.close()
            return self._settings_cache
        except Exception as e:
            logger.error(f"Failed to fetch dynamic settings: {e}")
            # Fallback to defaults from ai_config
            return {
                "llm_model": ai_config.LLM_MODEL,
                "llm_fast_model": ai_config.LLM_FAST_MODEL,
                "temperature": ai_config.TEMPERATURE,
                "max_tokens": ai_config.MAX_TOKENS,
                "top_p": ai_config.TOP_P,
                "stt_engine": "deepgram",
                "groq_whisper_model": ai_config.GROQ_WHISPER_MODEL,
                "deepgram_model": ai_config.DEEPGRAM_MODEL
            }

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generates 384-dimensional vector embeddings for semantic search.
        Using local SentenceTransformer (Free).
        """
        if not text or not text.strip():
            return [0.0] * 384

        model = self._get_local_embedding_model()
        if model:
            try:
                # Synchronous call in an async wrapper
                embedding = model.encode(text)
                return embedding.tolist()
            except Exception as e:
                logger.warning(f"Local embedding failed: {e}")

        # Tier 2: Hash-based deterministic pseudo-embedding (Ultimate fallback)
        logger.warning("Using hash-based fallback for embedding")
        hash_obj = hashlib.sha256(text.encode())
        hash_hex = hash_obj.hexdigest()
        result = []
        for i in range(0, len(hash_hex), 2):
            val = int(hash_hex[i:i+2], 16) / 255.0
            result.append(val)
        
        # Tile to reach 384
        while len(result) < 384:
            result.extend(result)
        return result[:384]

    async def transcribe_with_failover(self, audio_path: str) -> Tuple[str, str]:
        """
        Implements PRIMARY (Deepgram) -> FAILOVER (Groq) engine logic.
        """
        if not os.path.exists(audio_path):
            raise AIServiceError(f"Audio file not found: {audio_path}")

        request_id = str(uuid.uuid4())
        
        settings = self._get_dynamic_settings()
        preferred_engine = settings["stt_engine"]

        # Try Preferred engine first
        if preferred_engine == "deepgram" and self.dg_client:
            try:
                self.request_tracker.start_request(request_id, "deepgram")
                with open(audio_path, "rb") as audio:
                    response = self.dg_client.listen.v1.media.transcribe_file(
                        request=audio.read(),
                        model=settings["deepgram_model"],
                        smart_format=True,
                    )
                    transcript = response.results.channels[0].alternatives[0].transcript
                    self.request_tracker.end_request(request_id, True)
                    return transcript, "deepgram"
            except Exception as e:
                logger.error(f"Deepgram transcription failed: {e}")
                self.request_tracker.end_request(request_id, False, str(e))
        
        elif preferred_engine == "groq" and self.groq_client:
            try:
                self.request_tracker.start_request(request_id, "groq")
                with open(audio_path, "rb") as audio:
                    translation = self.groq_client.audio.transcriptions.create(
                        file=(os.path.basename(audio_path), audio.read()),
                        model=settings["groq_whisper_model"],
                        response_format="text",
                    )
                    self.request_tracker.end_request(request_id, True)
                    return translation, "groq"
            except Exception as e:
                logger.error(f"Groq transcription failed: {e}")
                self.request_tracker.end_request(request_id, False, str(e))

        # Ultimate Failover (Reverse of preferred)
        failover_engine = "groq" if preferred_engine == "deepgram" else "deepgram"
        
        if failover_engine == "deepgram" and self.dg_client:
            try:
                self.request_tracker.start_request(request_id, "deepgram-failover")
                with open(audio_path, "rb") as audio:
                    response = self.dg_client.listen.v1.media.transcribe_file(
                        request=audio.read(),
                        model=settings["deepgram_model"],
                        smart_format=True,
                    )
                    transcript = response.results.channels[0].alternatives[0].transcript
                    self.request_tracker.end_request(request_id, True)
                    return transcript, "deepgram"
            except Exception as e:
                logger.error(f"Deepgram failover failed: {e}")

        elif failover_engine == "groq" and self.groq_client:
            try:
                self.request_tracker.start_request(request_id, "groq-failover")
                with open(audio_path, "rb") as audio:
                    translation = self.groq_client.audio.transcriptions.create(
                        file=(os.path.basename(audio_path), audio.read()),
                        model=settings["groq_whisper_model"],
                        response_format="text",
                    )
                    self.request_tracker.end_request(request_id, True)
                    return translation, "groq"
            except Exception as e:
                logger.error(f"Groq failover failed: {e}")

        raise AIServiceError("All transcription engines failed or are not configured.")

    @retry_with_backoff(max_attempts=3)
    async def llm_brain(self, transcript: str, user_role: str = "ASSISTANT", user_instruction: str = "") -> NoteAIOutput:
        """
        Structured extraction using Llama 3.1 on Groq with robust validation.
        """
        # Validation
        transcript = validate_transcript(transcript)
        
        if not self.groq_client:
            return NoteAIOutput(
                title="Untitled Note", 
                summary="AI analysis unavailable (No API key)", 
                priority="MEDIUM", 
                transcript=transcript, 
                tasks=[]
            )

        system_prompt = ai_config.EXTRACTION_SYSTEM_PROMPT
        if user_role:
            system_prompt = f"{system_prompt}\n\nYou are acting as a {user_role}."
        
        user_content = f"Instruction: {user_instruction or 'Analyze the transcript.'}\n\nTranscript:\n{transcript}"

        settings = self._get_dynamic_settings()
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                model=settings["llm_model"],
                response_format={"type": "json_object"},
                temperature=settings["temperature"],
                max_tokens=settings["max_tokens"]
            )
            
            content = response.choices[0].message.content
            data = validate_json_response(content)
            
            # Additional structural validation
            title = data.get("title", "Untitled Note")[:100]
            summary = data.get("summary", "No summary generated.")
            priority = data.get("priority", "MEDIUM").upper()
            if priority not in ["HIGH", "MEDIUM", "LOW"]:
                priority = "MEDIUM"
            
            tasks = []
            for t in data.get("tasks", []):
                tasks.append({
                    "title": t.get("title", "Task")[:200],
                    "priority": t.get("priority", "MEDIUM").upper(),
                    "due_date": t.get("due_date")
                })

            return NoteAIOutput(
                title=title,
                summary=summary,
                priority=priority,
                transcript=transcript,
                tasks=tasks
            )
        except Exception as e:
            logger.error(f"LLM brain failed for {user_role}: {e}")
            raise # Let retry decorator handle it or fail final attempt

    async def run_full_analysis(self, audio_path: str) -> NoteAIOutput:
        """
        Orchestrates complete audio -> transcript -> AI analysis pipeline.
        """
        # 1. Transcribe
        transcript, engine = await self.transcribe_with_failover(audio_path)
        
        # 2. Analyze
        ai_output = await self.llm_brain(transcript)
        
        return ai_output

    @retry_with_backoff(max_attempts=2)
    async def detect_conflicts(self, new_summary: str, existing_notes: list[str]) -> list[dict]:
        """
        Detect contradictions or conflicts using LLM with centralized prompt.
        """
        if not existing_notes or not self.groq_client:
            return []

        # Optimization: Don't pass too many notes to preserve context window
        context_notes = existing_notes[-10:] # Limit to last 10 notes for relevance
        
        formatted_notes = "\n---\n".join([f"Note {i+1}: {note}" for i, note in enumerate(context_notes)])
        prompt = ai_config.CONFLICT_DETECTOR_PROMPT.format(
            new_summary=new_summary,
            existing_notes=formatted_notes
        )

        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=ai_config.LLM_FAST_MODEL, # Use faster/cheaper model for conflict detection
                response_format={"type": "json_object"}
            )
            data = validate_json_response(response.choices[0].message.content)
            return data.get("conflicts", [])
        except Exception as e:
            logger.error(f"Conflict detection failed: {e}")
            return []

    async def semantic_analysis(self, transcript: str, user_role: str = "GENERIC") -> dict:
        """
        Deep semantic analysis: emotional tone, patterns, logical consistency.
        """
        settings = self._get_dynamic_settings()
        
        system_prompt = f"""
        Role: SEMANTIC_ANALYST (Expert in psychology, linguistics, and logical reasoning)
        Background: You are analyzing a voice note from a {user_role}.
        
        Task: Provide a deep semantic analysis of the transcript.
        Output MUST be a JSON object with:
        - sentiment: string ("Positive", "Negative", "Neutral", "Mixed")
        - key_insights: list of strings (depth beyond summary)
        - logical_patterns: list of strings (hidden assumptions, logical flow)
        - suggested_questions: list of strings (what should the user ask themselves next?)
        - emotional_tone: string (e.g. "Anxious but determined", "Joyful", "Professional")
        - actionable_hidden_tasks: list of strings (non-obvious things to do)
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ],
                model=settings["llm_model"],
                response_format={"type": "json_object"},
                temperature=0.5 # Slightly higher for more creative analysis
            )
            data = validate_json_response(response.choices[0].message.content)
            return data
        except Exception as e:
            logger.error(f"Semantic analysis failed: {e}")
            raise AIServiceError(f"Failed to perform semantic analysis: {str(e)}")
