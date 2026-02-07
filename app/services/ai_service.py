import logging
import os
import time
import uuid
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from app.core.config import ai_config
from app.db import models
from app.db.session import SessionLocal
from app.schemas.note import NoteAIOutput
from app.utils.ai_service_utils import (
    AIServiceError,
    get_request_tracker,
    retry_with_backoff,
    validate_json_response,
    validate_transcript,
)

logger = logging.getLogger("VoiceNote")


class AIService:
    _local_embedding_model = None  # Class-level singleton
    _groq_client = None
    _dg_client = None

    def __init__(self):
        # AI API Keys from environment
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.dg_api_key = os.getenv("DEEPGRAM_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")
        self.request_tracker = get_request_tracker()
        self._diarization_pipeline = None

    @property
    def groq_client(self):
        if AIService._groq_client is None and self.groq_api_key:
            from groq import Groq

            AIService._groq_client = Groq(api_key=self.groq_api_key)
        return AIService._groq_client

    @property
    def dg_client(self):
        if AIService._dg_client is None and self.dg_api_key:
            from deepgram import DeepgramClient

            AIService._dg_client = DeepgramClient(api_key=self.dg_api_key)
        return AIService._dg_client

    def _get_diarization_pipeline(self):
        """Lazy load diarization pipeline."""
        if (
            self._diarization_pipeline is None
            and self.hf_token
            and os.getenv("ENABLE_AI_PIPELINES", "false") == "true"
        ):
            try:
                logger.info("Loading Speaker Diarization pipeline...")
                from pyannote.audio import Pipeline

                self._diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization@2.1", use_auth_token=self.hf_token
                )
            except Exception as e:
                logger.error(f"Failed to load speaker diarization: {e}")
        return self._diarization_pipeline

    def _get_local_embedding_model(self):
        if AIService._local_embedding_model is None:
            try:
                # Using all-MiniLM-L6-v2 which produces 384 dimensions
                logger.info("Loading local embedding model: all-MiniLM-L6-v2")
                from sentence_transformers import SentenceTransformer

                AIService._local_embedding_model = SentenceTransformer(
                    "all-MiniLM-L6-v2"
                )
            except Exception as e:
                logger.error(f"Failed to load local embedding model: {e}")
        return AIService._local_embedding_model

    def _get_dynamic_settings(self):
        """Fetches settings from DB with a simple cache."""
        # Check cache (1 min)
        if hasattr(self, "_settings_cache") and (
            time.time() - self._settings_last_fetch < 60
        ):
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
                "deepgram_model": settings.deepgram_model,
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
                "deepgram_model": ai_config.DEEPGRAM_MODEL,
            }

    @lru_cache(maxsize=100)
    def _generate_embedding_cached(self, text: str) -> List[float]:
        """Internal cached method for embedding generation."""
        model = self._get_local_embedding_model()
        if not model:
            return []

        # CPU-bound computation
        embedding = model.encode(text)
        return embedding.tolist()

    def generate_embedding_sync(self, text: str) -> List[float]:
        """
        Synchronous wrapper that uses LRU cache.
        """
        if not text or not text.strip():
            return [0.0] * 384

        emb = self._generate_embedding_cached(text)
        return emb if emb else [0.0] * 384

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generates 384-dimensional vector embeddings for semantic search.
        Using local SentenceTransformer (Free).
        """
        return self.generate_embedding_sync(text)

    def transcribe_with_failover_sync(
        self,
        audio_path: str,
        languages: Optional[List[str]] = None,
        stt_model: str = "nova",
    ) -> Tuple[str, str, List[str], Dict[str, str]]:
        """
        STT with failover and explicit model selection.
        stt_model: 'nova', 'whisper', or 'both'
        Returns: (primary_transcript, engine_used, languages, all_transcripts_dict)
        """
        if not os.path.exists(audio_path):
            raise AIServiceError(f"Audio file not found: {audio_path}")

        request_id = str(uuid.uuid4())
        settings = self._get_dynamic_settings()

        results = {}
        primary_transcript = ""
        engine_used = ""
        used_langs = languages or ["en"]

        # 1. Prepare Deepgram Logic
        dg_params = {"model": settings["deepgram_model"], "smart_format": True}
        if languages:
            if len(languages) == 1:
                dg_params["language"] = languages[0]
            else:
                dg_params["detect_language"] = True
        else:
            dg_params["detect_language"] = True

        # 2. Prepare Groq Logic
        groq_params = {
            "model": settings["groq_whisper_model"],
            "response_format": "text",
        }
        if languages:
            groq_params["language"] = languages[0]

        def run_dg():
            if not self.dg_client:
                return None
            try:
                with open(audio_path, "rb") as file:
                    buffer_data = file.read()
                    # For SDK v5.x (Generated version)
                    resp = self.dg_client.listen.v1.media.transcribe_file(
                        buffer_data,
                        model=settings["deepgram_model"],
                        smart_format=True,
                    )
                    return resp.results.channels[0].alternatives[0].transcript
            except Exception as e:
                logger.error(f"Deepgram failed: {e}")
                return None

        def run_groq():
            if not self.groq_client:
                return None
            try:
                with open(audio_path, "rb") as file:
                    return self.groq_client.audio.transcriptions.create(
                        file=(os.path.basename(audio_path), file.read()), **groq_params
                    )
            except Exception as e:
                logger.error(f"Groq failed: {e}")
                return None

        # Execute based on preference
        if stt_model == "both":
            # Run both sequentially in worker context
            dg_t = run_dg() if self.dg_client else None
            groq_t = run_groq() if self.groq_client else None

            if dg_t:
                results["deepgram"] = dg_t
            if groq_t:
                results["groq"] = groq_t

            primary_transcript = dg_t or groq_t or ""
            engine_used = "both"
        elif stt_model == "whisper":
            groq_t = run_groq()
            if groq_t:
                primary_transcript = groq_t
                engine_used = "groq"
                results["groq"] = groq_t
            else:  # Fallback to DG
                dg_t = run_dg()
                primary_transcript = dg_t or ""
                engine_used = "deepgram" if dg_t else "failed"
                if dg_t:
                    results["deepgram"] = dg_t
        else:  # Default: Nova
            dg_t = run_dg()
            if dg_t:
                primary_transcript = dg_t
                engine_used = "deepgram"
                results["deepgram"] = dg_t
            else:  # Fallback to Groq
                groq_t = run_groq()
                primary_transcript = groq_t or ""
                engine_used = "groq" if groq_t else "failed"
                if groq_t:
                    results["groq"] = groq_t
                primary_transcript = groq_t or ""
                engine_used = "groq" if groq_t else "failed"

        logger.info(
            f"STT Complete: engine={engine_used}, transcript_type={type(primary_transcript)}"
        )
        if not primary_transcript:
            error_details = []
            if not self.dg_client:
                error_details.append("Deepgram client missing")
            if not self.groq_client:
                error_details.append("Groq client missing")

            # Check if results had keys but empty values (silence)
            is_silence = any(v == "" for v in results.values())
            if is_silence:
                raise AIServiceError(
                    "STT silent: The audio contains no detectable speech."
                )

            raise AIServiceError(
                f"All STT engines failed. Details: {', '.join(error_details) if error_details else 'Unknown error (check logs)'}"
            )

        return primary_transcript, engine_used, used_langs, results

    def run_full_analysis_sync(
        self,
        audio_path: str,
        user_role: str = "GENERIC",
        languages: Optional[List[str]] = None,
        stt_model: str = "nova",
        **kwargs,
    ) -> NoteAIOutput:
        """Synchronous orchestration with model selection."""
        transcript, engine, detected_langs, all_transcripts = (
            self.transcribe_with_failover_sync(
                audio_path, languages=languages, stt_model=stt_model
            )
        )
        ai_output = self.llm_brain_sync(transcript, user_role, **kwargs)
        # Store metadata for the worker to save
        ai_output.metadata = {
            "engine": engine,
            "languages": detected_langs,
            "all_transcripts": all_transcripts,
        }
        return ai_output

    async def transcribe_with_failover(
        self,
        audio_path: str,
        languages: Optional[List[str]] = None,
        stt_model: str = "nova",
    ) -> Tuple[str, str, List[str], Dict[str, str]]:
        """
        Async wrapper for transcription with model selection.
        """
        return self.transcribe_with_failover_sync(
            audio_path, languages=languages, stt_model=stt_model
        )

    def llm_brain_sync(
        self,
        transcript: str,
        user_role: str = "GENERIC",
        user_instruction: str = "",
        note_created_at: Optional[int] = None,
        user_timezone: str = "UTC",
        **kwargs,
    ) -> NoteAIOutput:
        """Synchronous structured extraction for Celery worker with timezone-aware priority."""
        # Validation
        transcript = validate_transcript(transcript)

        if not self.groq_client:
            return NoteAIOutput(
                title="Untitled Note",
                summary="AI analysis unavailable (No API key)",
                priority="MEDIUM",
                transcript=transcript,
                tasks=[],
            )

        system_prompt = ai_config.EXTRACTION_SYSTEM_PROMPT
        if user_role:
            system_prompt = f"{system_prompt}\n\nYou are acting as a {user_role}."

        # Inject Domain Terminology (Jargons)
        jargons = kwargs.get("jargons", [])
        if jargons:
            system_prompt += f"\n\nCRITICAL CONTEXT: The following industry-specific terms or 'jargons' are relevant to this user. Use them correctly if they appear phonetically or contextually:\n{', '.join(jargons)}"

        # NEW: Add temporal context for intelligent priority assignment
        if note_created_at:
            try:
                from datetime import datetime

                import pytz

                # Convert timestamp to user's local time
                tz = pytz.timezone(user_timezone)
                note_time = datetime.fromtimestamp(note_created_at / 1000, tz=tz)
                current_time = datetime.now(tz)

                temporal_context = f"""

TEMPORAL CONTEXT (CRITICAL FOR PRIORITY ASSIGNMENT):
- Note was recorded at: {note_time.strftime('%Y-%m-%d %H:%M:%S %Z')}
- Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}
- User timezone: {user_timezone}
- Time elapsed since note: {(current_time - note_time).total_seconds() / 3600:.1f} hours

Use this temporal context to intelligently assign task priorities based on urgency and deadlines.
"""
                system_prompt += temporal_context
            except Exception as e:
                logger.warning(f"Failed to add temporal context: {e}")

        user_content = f"Instruction: {user_instruction or 'Analyze the transcript.'}\n\nTranscript:\n{transcript}"
        settings = self._get_dynamic_settings()

        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                model=settings["llm_model"],
                response_format={"type": "json_object"},
                temperature=settings["temperature"],
                max_tokens=settings["max_tokens"],
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
                # Robust extraction for title and description
                task_title = t.get("title") or t.get("description", "Task")[:100]
                task_description = t.get("description") or t.get(
                    "title", "No description provided."
                )
                tasks.append(
                    {
                        "title": task_title,
                        "description": task_description,
                        "priority": t.get("priority", "MEDIUM").upper(),
                        "deadline": t.get("deadline") or t.get("due_date"),
                        "actions": t.get("actions", {}),  # Pass through actions
                    }
                )

            tags = data.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            return NoteAIOutput(
                title=title,
                summary=summary,
                priority=priority,
                transcript=transcript,
                tasks=tasks,
                tags=tags,
            )
        except Exception as e:
            logger.error(f"LLM brain failed for {user_role}: {e}")
            raise

    @retry_with_backoff(max_attempts=3)
    async def llm_brain(
        self,
        transcript: str,
        user_role: str = "GENERIC",
        user_instruction: str = "",
        note_created_at: Optional[int] = None,
        user_timezone: str = "UTC",
        **kwargs,
    ) -> NoteAIOutput:
        """Structured extraction using Llama 3.1 on Groq with robust validation."""
        return self.llm_brain_sync(
            transcript,
            user_role,
            user_instruction,
            note_created_at,
            user_timezone,
            **kwargs,
        )

    async def run_full_analysis(
        self, audio_path: str, user_role: str = "GENERIC", **kwargs
    ) -> NoteAIOutput:
        """
        Orchestrates complete audio -> transcript -> AI analysis pipeline.
        """
        # 1. Transcribe
        transcript, engine = await self.transcribe_with_failover(audio_path)

        # 2. Analyze
        ai_output = await self.llm_brain(transcript, user_role, **kwargs)

        return ai_output

    def detect_conflicts_sync(
        self, new_summary: str, context_items: List[str], context_type: str = "schedule"
    ) -> List[Dict]:
        """
        Detect contradictions between a new summary and existing context (events or notes).
        """
        if not context_items or not self.groq_client:
            return []

        # Optimization: Limit context
        final_context = context_items[-15:]
        formatted_context = "\n---\n".join(
            [f"Item {i+1}: {item}" for i, item in enumerate(final_context)]
        )

        prompt = f"""
        Role: CONFLICT_DETECTOR
        Task: Identify any contradictions or major inconsistencies between the NEW_STORY and the EXISTING_{context_type.upper()}.
        
        NEW_STORY (Current Note Summary):
        {new_summary}
        
        EXISTING_{context_type.upper()}:
        {formatted_context}
        
        Return a JSON object with a 'conflicts' key containing a list:
        {{
            "conflicts": [
                {{"fact": "statement A", "conflict": "statement B", "explanation": "why they conflict", "severity": "HIGH/MEDIUM"}}
            ]
        }}
        If no conflicts, return {{"conflicts": []}}.
        """

        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=ai_config.LLM_FAST_MODEL,
                response_format={"type": "json_object"},
            )
            data = validate_json_response(response.choices[0].message.content)
            return data.get("conflicts", [])
        except Exception as e:
            logger.error(f"Sync conflict detection failed ({context_type}): {e}")
            return []

    @retry_with_backoff(max_attempts=2)
    async def detect_conflicts(
        self, new_summary: str, existing_notes: list[str]
    ) -> list[dict]:
        """
        Detect contradictions or conflicts using LLM with centralized prompt.
        """
        if not existing_notes or not self.groq_client:
            return []

        # Optimization: Don't pass too many notes to preserve context window
        context_notes = existing_notes[-10:]  # Limit to last 10 notes for relevance

        formatted_notes = "\n---\n".join(
            [f"Note {i+1}: {note}" for i, note in enumerate(context_notes)]
        )
        prompt = ai_config.CONFLICT_DETECTOR_PROMPT.format(
            new_summary=new_summary, existing_notes=formatted_notes
        )

        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=ai_config.LLM_FAST_MODEL,  # Use faster/cheaper model for conflict detection
                response_format={"type": "json_object"},
            )
            data = validate_json_response(response.choices[0].message.content)
            return data.get("conflicts", [])
        except Exception as e:
            logger.error(f"Conflict detection failed: {e}")
            return []

    def semantic_analysis_sync(
        self, transcript: str, user_role: str = "GENERIC", **kwargs
    ) -> dict:
        """Synchronous version for Celery worker."""
        settings = self._get_dynamic_settings()

        jargons = kwargs.get("jargons", [])
        personal_instruction = kwargs.get("personal_instruction", "")

        system_prompt = f"""
        Role: SEMANTIC_ANALYST (Expert in psychology, linguistics, and logical reasoning)
        Background: You are analyzing a voice note from a {user_role}.
        
        Personal User Context: {personal_instruction}
        Relevant Jargons: {", ".join(jargons)}
        
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
                    {"role": "user", "content": transcript},
                ],
                model=settings["llm_model"],
                response_format={"type": "json_object"},
                temperature=0.5,
            )
            data = validate_json_response(response.choices[0].message.content)
            # Match schema expected by background task
            return type(
                "Analysis",
                (),
                {
                    "sentiment": data.get("sentiment"),
                    "tone": data.get("emotional_tone"),
                    "hidden_patterns": data.get("logical_patterns"),
                    "suggested_questions": data.get("suggested_questions"),
                },
            )
        except Exception as e:
            logger.error(f"Semantic analysis failed: {e}")
            raise

    async def semantic_analysis(
        self, transcript: str, user_role: str = "GENERIC", **kwargs
    ) -> dict:
        """Deep semantic analysis: emotional tone, patterns, logical consistency."""
        return self.semantic_analysis_sync(transcript, user_role, **kwargs)
