import os
import json
import asyncio
import time
import uuid
import logging
from groq import Groq
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from pyannote.audio import Pipeline
import torch
from app.core.config_ai import ai_config
from app.schemas.note_schema import NoteAIOutput
from app.utils.ai_service_utils import (
    retry_with_backoff,
    with_timeout,
    validate_transcript,
    validate_ai_response,
    validate_json_response,
    RequestTracker,
    RateLimiter,
    AIServiceError,
    TimeoutError as AITimeoutError,
    get_request_tracker
)

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.dg_client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
        self.request_tracker = get_request_tracker()
        
        # Phase 2: Rate limiters for different services
        # Groq: 30 requests per minute (conservative estimate)
        self.groq_limiter = RateLimiter(max_requests=30, time_window=60.0)
        # Deepgram: 50 requests per minute
        self.deepgram_limiter = RateLimiter(max_requests=50, time_window=60.0)
        
        # Initialize Pyannote for Whisper Diarization
        self.diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.getenv("HUGGINGFACE_TOKEN")
        )
        if torch.cuda.is_available():
            self.diarization_pipeline.to(torch.device("cuda"))

    def _apply_diarization(self, audio_path: str, whisper_json: dict) -> str:
        """Aligns Whisper segments with Pyannote speaker timestamps."""
        diarization = self.diarization_pipeline(audio_path)
        
        # Logic to map whisper words to speakers based on timestamps
        annotated_transcript = []
        for segment in whisper_json['segments']:
            start = segment['start']
            text = segment['text']
            
            # Find the speaker active at this timestamp
            speaker = "Unknown"
            for turn, _, speaker_label in diarization.itertracks(yield_label=True):
                if turn.start <= start <= turn.end:
                    speaker = f"Speaker {speaker_label}"
                    break
            
            annotated_transcript.append(f"{speaker}: {text.strip()}")
            
        return "\n".join(annotated_transcript)

    @retry_with_backoff(max_attempts=3, initial_backoff=1.0, exceptions=(Exception,))
    async def transcribe_with_groq(self, audio_path: str) -> str:
        """
        Phase 2: Full Whisper transcription with external Pyannote diarization.
        
        Features:
        - Retry logic with exponential backoff (up to 3 attempts)
        - Rate limiting to prevent API throttling
        - Request tracking for monitoring
        - Timeout protection
        """
        request_id = str(uuid.uuid4())[:8]
        
        try:
            # Phase 2: Rate limiting check
            if not self.groq_limiter.allow_request():
                wait_time = self.groq_limiter.get_wait_time()
                logger.warning(f"Rate limit hit. Waiting {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)
            
            # Phase 2: Track request
            self.request_tracker.start_request(
                request_id, 
                "groq_transcription", 
                audio_path=audio_path,
                model=ai_config.GROQ_WHISPER_MODEL
            )
            
            # Phase 2: Timeout protection (30s)
            async def _do_transcribe():
                with open(audio_path, "rb") as file:
                    transcription = self.groq_client.audio.transcriptions.create(
                        file=(audio_path, file.read()),
                        model=ai_config.GROQ_WHISPER_MODEL,
                        response_format="verbose_json"  # Needed for segment timestamps
                    )
                return transcription.model_dump()
            
            try:
                transcript_data = await asyncio.wait_for(_do_transcribe(), timeout=30.0)
            except asyncio.TimeoutError:
                self.request_tracker.end_request(request_id, success=False, error_msg="Timeout")
                raise AITimeoutError("Groq transcription timed out after 30s")
            
            # Apply Diarization
            result = self._apply_diarization(audio_path, transcript_data)
            self.request_tracker.end_request(request_id, success=True)
            logger.info(f"✅ Groq transcription succeeded (request {request_id})")
            return result
            
        except FileNotFoundError:
            self.request_tracker.end_request(request_id, success=False, error_msg="File not found")
            raise ValueError(f"Audio file not found: {audio_path}")
        except AITimeoutError:
            raise
        except Exception as e:
            self.request_tracker.end_request(request_id, success=False, error_msg=str(e))
            raise RuntimeError(f"Groq transcription failed: {str(e)}")

    @retry_with_backoff(max_attempts=3, initial_backoff=1.0, exceptions=(Exception,))
    async def transcribe_with_deepgram(self, audio_path: str) -> str:
        """
        Phase 2: Native Deepgram Nova-3 transcription with internal diarization.
        
        Features:
        - Retry logic with exponential backoff (up to 3 attempts)
        - Rate limiting to prevent API throttling
        - Request tracking for monitoring
        - Timeout protection
        """
        request_id = str(uuid.uuid4())[:8]
        
        try:
            # Phase 2: Rate limiting check
            if not self.deepgram_limiter.allow_request():
                wait_time = self.deepgram_limiter.get_wait_time()
                logger.warning(f"Rate limit hit. Waiting {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)
            
            # Phase 2: Track request
            self.request_tracker.start_request(
                request_id,
                "deepgram_transcription",
                audio_path=audio_path,
                model=ai_config.DEEPGRAM_MODEL
            )
            
            # Phase 2: Timeout protection (30s)
            async def _do_transcribe():
                with open(audio_path, "rb") as audio:
                    payload: FileSource = {"buffer": audio.read()}
                
                options = PrerecordedOptions(
                    model=ai_config.DEEPGRAM_MODEL,
                    smart_format=True,
                    diarize=True,
                    punctuate=True
                )
                response = await self.dg_client.listen.asyncprerecorded.v("1").transcribe_file(
                    payload, options
                )
                return response
            
            try:
                response = await asyncio.wait_for(_do_transcribe(), timeout=30.0)
            except asyncio.TimeoutError:
                self.request_tracker.end_request(request_id, success=False, error_msg="Timeout")
                raise AITimeoutError("Deepgram transcription timed out after 30s")
            
            result = response.results.channels[0].alternatives[0].transcript
            self.request_tracker.end_request(request_id, success=True)
            logger.info(f"✅ Deepgram transcription succeeded (request {request_id})")
            return result
            
        except FileNotFoundError:
            self.request_tracker.end_request(request_id, success=False, error_msg="File not found")
            raise ValueError(f"Audio file not found: {audio_path}")
        except AITimeoutError:
            raise
        except Exception as e:
            self.request_tracker.end_request(request_id, success=False, error_msg=str(e))
            raise RuntimeError(f"Deepgram transcription failed: {str(e)}")

    @retry_with_backoff(max_attempts=3, initial_backoff=1.0, exceptions=(Exception,))
    async def llm_brain(
        self, 
        transcript: str, 
        user_role: str, 
        user_instruction: str = None,
        request_id: str = None
    ) -> NoteAIOutput:
        """
        Phase 2: Reasoning engine with optional user prompt support and error handling.
        
        Features:
        - Retry logic with exponential backoff (up to 3 attempts)
        - Rate limiting to prevent API throttling
        - Request tracking for monitoring
        - Timeout protection (30s)
        - Comprehensive input/output validation
        - Confidence scoring in response
        """
        if not request_id:
            request_id = str(uuid.uuid4())[:8]
        
        try:
            # Phase 2: Input validation using dedicated validator
            try:
                transcript = validate_transcript(transcript)
            except AIServiceError as e:
                raise ValueError(f"Invalid transcript: {str(e)}")
            
            # Phase 2: Rate limiting check
            if not self.groq_limiter.allow_request():
                wait_time = self.groq_limiter.get_wait_time()
                logger.warning(f"Rate limit hit. Waiting {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)
            
            # Phase 2: Track request
            self.request_tracker.start_request(
                request_id,
                "llm_processing",
                model=ai_config.LLM_MODEL,
                user_role=user_role
            )
            
            # Build System Prompt dynamically
            instruction_part = f"\nUser specific instruction: {user_instruction}" if user_instruction else ""
            system_msg = f"{ai_config.BASE_SYSTEM_PROMPT}\nUser Role context: {user_role}{instruction_part}"
            
            # Phase 2: Timeout protection (30s)
            async def _do_llm_call():
                return self.groq_client.chat.completions.create(
                    model=ai_config.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": f"Please process the following transcript:\n\n{transcript}"}
                    ],
                    temperature=ai_config.TEMPERATURE,
                    max_tokens=ai_config.MAX_TOKENS,
                    top_p=ai_config.TOP_P,
                    response_format={"type": "json_object"}
                )
            
            try:
                completion = await asyncio.wait_for(_do_llm_call(), timeout=30.0)
            except asyncio.TimeoutError:
                self.request_tracker.end_request(request_id, success=False, error_msg="Timeout")
                raise AITimeoutError("LLM call timed out after 30s")
            
            # Phase 2: Response validation
            if not completion or not completion.choices or len(completion.choices) == 0:
                self.request_tracker.end_request(request_id, success=False, error_msg="Empty response")
                raise ValueError("Empty response from LLM")
            
            # Phase 2: JSON validation
            try:
                raw_json = validate_json_response(completion.choices[0].message.content)
            except AIServiceError as e:
                self.request_tracker.end_request(request_id, success=False, error_msg=str(e))
                raise ValueError(f"LLM response validation failed: {str(e)}")
            
            # Parse and Validate with Pydantic
            ai_output = NoteAIOutput(**raw_json)
            
            self.request_tracker.end_request(request_id, success=True)
            logger.info(f"✅ LLM brain processing succeeded (request {request_id})")
            return ai_output
            
        except ValueError:
            raise
        except AITimeoutError:
            raise
        except json.JSONDecodeError as e:
            self.request_tracker.end_request(request_id, success=False, error_msg=str(e))
            raise ValueError(f"LLM response was not valid JSON: {str(e)}")
        except Exception as e:
            self.request_tracker.end_request(request_id, success=False, error_msg=str(e))
            raise RuntimeError(f"LLM brain processing failed: {str(e)}")