from fastapi import APIRouter, UploadFile, File, Response
from fastapi.responses import FileResponse
from app.services.ai_service import AIService
from app.core.audio import preprocess_audio_pipeline
import shutil
import os
import uuid
from slowapi import Limiter
from slowapi.util import get_remote_address
test_router = APIRouter(prefix="/api/test", tags=["Testing Lab"])
ai_service = AIService()
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://redis:6379/0")

@test_router.post("/stt-comparison")
@limiter.limit("5/minute")
async def stt_comparison(file: UploadFile = File(...)):
    """
    POST /stt-comparison: Dual STT Test.
    Returns Groq Whisper and Deepgram Nova-3 side-by-side.
    """
    temp_id = str(uuid.uuid4())
    temp_path = f"uploads/test_{temp_id}_{file.filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run STT concurrently
    import asyncio
    groq_text, dg_text = await asyncio.gather(
        ai_service.transcribe_with_groq(temp_path),
        ai_service.transcribe_with_deepgram(temp_path)
    )

    return {
        "filename": file.filename,
        "groq_whisper_v3_turbo": groq_text,
        "deepgram_nova_3": dg_text,
        "comparison_tip": "Check for punctuation and technical jargon accuracy."
    }

@test_router.post("/preprocess")
async def audio_lab_preprocess(file: UploadFile = File(...)):
    """
    POST /preprocess: Audio Lab.
    Upload a file, get the Enhanced/High-Gain version back immediately.
    """
    temp_id = str(uuid.uuid4())
    input_path = f"uploads/lab_in_{temp_id}.mp3"
    
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run our enhancement pipeline (Noise removal + AGC + Normalization)
    enhanced_path = preprocess_audio_pipeline(input_path)

    # Return the file for you to listen to in your browser/postman
    return FileResponse(
        path=enhanced_path, 
        media_type="audio/wav", 
        filename=f"enhanced_{file.filename}.wav"
    )