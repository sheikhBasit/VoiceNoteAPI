import os
import json
import asyncio
from groq import Groq
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from pyannote.audio import Pipeline
import torch
from app.core.config_ai import ai_config
from app.schemas.note_schema import NoteAIOutput

class AIService:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.dg_client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
        
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

    async def transcribe_with_groq(self, audio_path: str) -> str:
        """Full Whisper transcription with external Pyannote diarization."""
        try:
            with open(audio_path, "rb") as file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=(audio_path, file.read()),
                    model=ai_config.GROQ_WHISPER_MODEL,
                    response_format="verbose_json" # Needed for segment timestamps
                )
            # Apply Diarization
            return self._apply_diarization(audio_path, transcription.model_dump())
        except FileNotFoundError:
            raise ValueError(f"Audio file not found: {audio_path}")
        except Exception as e:
            raise RuntimeError(f"Groq transcription failed: {str(e)}")

    async def transcribe_with_deepgram(self, audio_path: str) -> str:
        """Native Deepgram Nova-3 transcription with internal diarization."""
        try:
            with open(audio_path, "rb") as audio:
                payload: FileSource = {"buffer": audio.read()}
            
            options = PrerecordedOptions(
                model=ai_config.DEEPGRAM_MODEL,
                smart_format=True,
                diarize=True,
                punctuate=True
            )
            response = await self.dg_client.listen.asyncprerecorded.v("1").transcribe_file(payload, options)
            return response.results.channels[0].alternatives[0].transcript
        except FileNotFoundError:
            raise ValueError(f"Audio file not found: {audio_path}")
        except Exception as e:
            raise RuntimeError(f"Deepgram transcription failed: {str(e)}")

    async def llm_brain(self, transcript: str, user_role: str, user_instruction: str = None) -> NoteAIOutput:
        """Reasoning engine with optional user prompt support and error handling."""
        try:
            # Validate inputs
            if not transcript or len(transcript.strip()) == 0:
                raise ValueError("Transcript cannot be empty")
            if len(transcript) > 100000:
                raise ValueError("Transcript too long (max 100,000 characters)")
            
            # Build System Prompt dynamically
            instruction_part = f"\nUser specific instruction: {user_instruction}" if user_instruction else ""
            system_msg = f"{ai_config.BASE_SYSTEM_PROMPT}\nUser Role context: {user_role}{instruction_part}"
            
            completion = self.groq_client.chat.completions.create(
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
            
            # ✅ VALIDATION: Check response exists
            if not completion or not completion.choices or len(completion.choices) == 0:
                raise ValueError("Empty response from LLM")
            
            # Parse and Validate with Pydantic
            raw_json = json.loads(completion.choices[0].message.content)
            return NoteAIOutput(**raw_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM response was not valid JSON: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"LLM brain processing failed: {str(e)}")