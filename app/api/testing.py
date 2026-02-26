import os
import shutil
import uuid

import redis
from celery.result import AsyncResult
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from slowapi.util import get_remote_address

from app.core.audio import preprocess_audio_pipeline
from app.services.ai_service import AIService
from app.worker.task import ping_task

test_router = APIRouter(prefix="/api/v1/test", tags=["Testing Lab"])
# ai_service is instantiated inside endpoints to avoid module-level hangs
# ai_service = AIService()
from app.core.limiter import limiter

from fastapi import APIRouter, Depends, File, Request, UploadFile


@test_router.post("/stt-comparison")
@limiter.limit("5/minute")
async def stt_comparison(request: Request, file: UploadFile = File(...)):
    """
    POST /stt-comparison: Dual STT Test.
    Returns Groq Whisper and Deepgram Nova-3 side-by-side.
    """
    temp_id = str(uuid.uuid4())
    temp_path = f"uploads/test_{temp_id}_{file.filename}"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run STT concurrently
    ai_service = AIService()
    import asyncio

    groq_text, dg_text = await asyncio.gather(
        ai_service.transcribe_with_groq(temp_path),
        ai_service.transcribe_with_deepgram(temp_path),
    )

    return {
        "filename": file.filename,
        "groq_whisper_v3_turbo": groq_text,
        "deepgram_nova_3": dg_text,
        "comparison_tip": "Check for punctuation and technical jargon accuracy.",
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
        filename=f"enhanced_{file.filename}.wav",
    )


@test_router.get("/celery")
async def test_celery_task():
    """
    GET /celery: Test Redis Queue (Celery).
    Triggers a background task and waits for the result.
    """
    task_id = str(uuid.uuid4())
    result = ping_task.delay(message=f"Hello from API {task_id}")
    return {
        "task_id": result.id,
        "status": "queued",
        "message": "Task submitted to Celery",
    }


@test_router.get("/celery/{task_id}")
async def get_celery_status(task_id: str):
    """
    GET /celery/{task_id}: Check status of a specific task.
    """
    task_result = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result,
    }


@test_router.get("/redis")
async def test_redis_connection():
    """
    GET /redis: Test Redis Cache Connectivity.
    Sets and Gets a value from Redis.
    """
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        r = redis.from_url(redis_url)

        # Test Set/Get
        key = f"test_key_{uuid.uuid4()}"
        r.set(key, "working", ex=60)
        value = r.get(key)

        info = r.info()

        return {
            "status": "connected",
            "val_check": value.decode("utf-8") if value else None,
            "version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
        }
    except Exception as e:
        return {"status": "error", "details": str(e)}


@test_router.post("/make-admin")
async def make_admin(user_id: str, db: Session = Depends(get_db)):
    """
    POST /make-admin: Promote a user to ADMIN role.
    Only available in non-production environments.
    """
    if os.getenv("ENVIRONMENT", "development") == "production":
        raise HTTPException(status_code=404, detail="Not available in production")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    user.primary_role = "ADMIN"
    db.commit()
    return {"message": f"User {user_id} is now an ADMIN", "role": user.primary_role}
