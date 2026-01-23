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
                    punctuate=True,
                    language="multi",  # Requirement: Polyglot Logic
                    detect_language=True
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
            
            # Specialized vocabulary modes (Requirement: Standout Strategy)
            mode_instruction = ""
            if "CRICKET" in user_role.upper():
                mode_instruction = "\nSPECIAL MODE: Using Cricket specialized vocabulary (wickets, crease, powerplay, etc.)"
            elif "QURANIC" in user_role.upper():
                mode_instruction = "\nSPECIAL MODE: Using Quranic/Religious terminology and context."

            system_msg = f"{ai_config.BASE_SYSTEM_PROMPT}\nUser Role context: {user_role}{mode_instruction}{instruction_part}"

            
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

    async def transcribe_with_failover(self, audio_path: str) -> tuple[str, str]:
        """
        Dual-Engine Transcription with automatic failover.
        
        Primary: Deepgram Nova-3 (optimized for low-latency, native diarization)
        Fallback: Groq Whisper-v3-Turbo (triggers on Deepgram 5xx or rate limits)
        
        Returns:
            tuple: (transcript, engine_used)
        """
        request_id = str(uuid.uuid4())[:8]
        
        # Try Deepgram first (Primary)
        try:
            logger.info(f"[{request_id}] Attempting PRIMARY engine: Deepgram Nova-3")
            transcript = await self.transcribe_with_deepgram(audio_path)
            logger.info(f"[{request_id}] ✅ Deepgram transcription succeeded")
            return transcript, "deepgram"
            
        except Exception as deepgram_error:
            error_str = str(deepgram_error).lower()
            
            # Check if it's a 5xx error or rate limit (should failover)
            is_server_error = any(code in error_str for code in ["500", "502", "503", "504", "5xx"])
            is_rate_limit = any(term in error_str for term in ["rate limit", "429", "too many requests", "quota"])
            is_timeout = "timeout" in error_str
            
            if is_server_error or is_rate_limit or is_timeout:
                logger.warning(
                    f"[{request_id}] ⚠️ Deepgram failed (failover triggered): {deepgram_error}"
                )
                
                # Failover to Groq Whisper
                try:
                    logger.info(f"[{request_id}] Attempting FAILOVER engine: Groq Whisper")
                    transcript = await self.transcribe_with_groq(audio_path)
                    logger.info(f"[{request_id}] ✅ Groq failover transcription succeeded")
                    return transcript, "groq"
                    
                except Exception as groq_error:
                    logger.error(f"[{request_id}] ❌ Both engines failed. Groq error: {groq_error}")
                    raise RuntimeError(
                        f"All transcription engines failed. "
                        f"Deepgram: {deepgram_error}, Groq: {groq_error}"
                    )
            else:
                # Non-recoverable error (e.g., file not found), don't failover
                logger.error(f"[{request_id}] ❌ Deepgram failed (non-recoverable): {deepgram_error}")
                raise

    def generate_embedding(self, text: str) -> list:
        """
        Generate 1536-dimensional vector embedding for semantic search.
        
        Uses OpenAI's text-embedding-3-small model via Groq-compatible endpoint
        or falls back to a local sentence-transformers model.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of 1536 floats representing the embedding vector
        """
        import numpy as np
        
        request_id = str(uuid.uuid4())[:8]
        
        try:
            self.request_tracker.start_request(
                request_id,
                "embedding_generation",
                text_length=len(text)
            )
            
            # Truncate text if too long (embedding models have limits)
            max_chars = 8000
            if len(text) > max_chars:
                text = text[:max_chars]
                logger.warning(f"[{request_id}] Text truncated to {max_chars} chars for embedding")
            
            # Clean the text
            text = text.strip()
            if not text:
                logger.warning(f"[{request_id}] Empty text, returning zero vector")
                self.request_tracker.end_request(request_id, success=True)
                return [0.0] * 1536
            
            # Try OpenAI-compatible embedding via environment variable
            openai_api_key = os.getenv("OPENAI_API_KEY")
            
            if openai_api_key:
                try:
                    import httpx
                    
                    response = httpx.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={
                            "Authorization": f"Bearer {openai_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "text-embedding-3-small",
                            "input": text
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        embedding = response.json()["data"][0]["embedding"]
                        self.request_tracker.end_request(request_id, success=True)
                        logger.info(f"[{request_id}] ✅ OpenAI embedding generated")
                        return embedding
                    else:
                        logger.warning(f"[{request_id}] OpenAI API error: {response.status_code}")
                        
                except Exception as openai_error:
                    logger.warning(f"[{request_id}] OpenAI embedding failed: {openai_error}")
            
            # Fallback: Use sentence-transformers locally
            try:
                from sentence_transformers import SentenceTransformer
                
                # Use a model that produces 1536-dim embeddings, or pad/truncate
                model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dim
                embedding_raw = model.encode(text).tolist()
                
                # Pad to 1536 dimensions if needed
                if len(embedding_raw) < 1536:
                    embedding = embedding_raw + [0.0] * (1536 - len(embedding_raw))
                else:
                    embedding = embedding_raw[:1536]
                
                self.request_tracker.end_request(request_id, success=True)
                logger.info(f"[{request_id}] ✅ Local embedding generated (sentence-transformers)")
                return embedding
                
            except ImportError:
                logger.warning(f"[{request_id}] sentence-transformers not installed")
            
            # Last resort: Generate deterministic pseudo-embedding from text hash
            logger.warning(f"[{request_id}] Using hash-based pseudo-embedding (not recommended for production)")
            import hashlib
            
            # Create reproducible embedding from text
            hash_bytes = hashlib.sha512(text.encode()).digest()
            # Expand to 1536 floats
            np.random.seed(int.from_bytes(hash_bytes[:4], 'big'))
            embedding = np.random.randn(1536).tolist()
            
            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = (np.array(embedding) / norm).tolist()
            
            self.request_tracker.end_request(request_id, success=True)
            return embedding
            
        except Exception as e:
            self.request_tracker.end_request(request_id, success=False, error_msg=str(e))
            logger.error(f"[{request_id}] ❌ Embedding generation failed: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536

    async def run_full_analysis(self, audio_path: str, user_role: str) -> 'NoteAIOutput':
        """
        Complete AI pipeline: Audio → Transcription → LLM Analysis → Structured Output
        
        This is the main orchestration method that:
        1. Transcribes audio using dual-engine failover
        2. Processes transcript with LLM for insights extraction
        3. Returns structured NoteAIOutput with title, summary, tasks, etc.
        
        Args:
            audio_path: Path to the preprocessed audio file
            user_role: User's role for context-aware processing
            
        Returns:
            NoteAIOutput: Structured analysis with title, summary, priority, transcript, tasks
        """
        from app.schemas.note import NoteAIOutput
        
        request_id = str(uuid.uuid4())[:8]
        logger.info(f"[{request_id}] 🚀 Starting full analysis pipeline")
        
        try:
            self.request_tracker.start_request(
                request_id,
                "full_analysis",
                audio_path=audio_path,
                user_role=user_role
            )
            
            # Step 1: Transcribe with failover
            logger.info(f"[{request_id}] Step 1/2: Transcription")
            transcript, engine_used = await self.transcribe_with_failover(audio_path)
            
            if not transcript or len(transcript.strip()) < 10:
                logger.warning(f"[{request_id}] Transcript too short or empty")
                # Return minimal output for empty transcripts
                self.request_tracker.end_request(request_id, success=True)
                return NoteAIOutput(
                    title="Empty Recording",
                    summary="No speech detected in this recording.",
                    priority="LOW",
                    transcript=transcript or "",
                    tasks=[]
                )
            
            # Step 2: LLM Analysis
            logger.info(f"[{request_id}] Step 2/2: LLM Analysis (engine: {engine_used})")
            ai_output = await self.llm_brain(
                transcript=transcript,
                user_role=user_role
            )
            
            # Ensure transcript from engine is preserved
            if not ai_output.transcript:
                ai_output.transcript = transcript
            
            self.request_tracker.end_request(request_id, success=True)
            logger.info(f"[{request_id}] ✅ Full analysis complete")
            
            return ai_output
            
        except Exception as e:
            self.request_tracker.end_request(request_id, success=False, error_msg=str(e))
            logger.error(f"[{request_id}] ❌ Full analysis failed: {e}")
            
            # Graceful degradation: Return raw transcript if LLM fails
            try:
                # Try to at least get the transcript
                transcript, _ = await self.transcribe_with_failover(audio_path)
                return NoteAIOutput(
                    title="Transcription Only",
                    summary="AI analysis failed. Raw transcript provided.",
                    priority="MEDIUM",
                    transcript=transcript,
                    tasks=[]
                )
            except:
                raise RuntimeError(f"Full analysis pipeline failed: {str(e)}")