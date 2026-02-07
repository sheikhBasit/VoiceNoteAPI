import os
import uuid
import time
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from celery import group

from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.db import models
from app.worker.task import note_process_pipeline
from app.utils.json_logger import JLogger

router = APIRouter(prefix="/api/v1/sync", tags=["Mobile Sync"])


@router.post("/upload-batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    POST /sync/upload-batch: Handles multiple files from the Kotlin "Sync Folder".
    Uses Celery group to process them in parallel.
    Docstring: Avoids N+1 queries by pre-creating note records and offloading processing.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    JLogger.info(
        "Processing batch upload", user_id=current_user.id, count=len(files)
    )

    tasks_to_group = []
    os.makedirs("uploads", exist_ok=True)

    user_role = (
        current_user.primary_role.name if current_user.primary_role else "GENERIC"
    )

    for file in files:
        note_id = str(uuid.uuid4())
        # Sanitizing path
        safe_filename = "".join(
            [c for c in file.filename if c.isalnum() or c in (".", "_", "-")]
        )
        local_path = f"uploads/{note_id}_{safe_filename}"

        # Save file to local storage for worker processing
        with open(local_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 1. Create Note record (Atomic for this batch step)
        new_note = models.Note(
            id=note_id,
            user_id=current_user.id,
            title=file.filename,
            summary="Processing batch upload from device sync...",
            status=models.NoteStatus.PENDING,
            audio_url=f"/{local_path}",
            raw_audio_url=f"/{local_path}",
            timestamp=int(time.time() * 1000),
        )
        db.add(new_note)

        # 2. Add to Celery Group Signature
        tasks_to_group.append(
            note_process_pipeline.s(
                note_id=note_id,
                local_file_path=local_path,
                user_role=user_role,
            )
        )

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        JLogger.error("Failed to commit batch notes", error=str(e))
        raise HTTPException(status_code=500, detail="Database error during batch prep")

    # 3. Parallel Execution via Celery Group
    # This ensures O(1) request time regardless of batch size
    job = group(tasks_to_group)()

    return {
        "status": "accepted",
        "batch_job_id": job.id,
        "processed_count": len(files),
        "message": "Files received and parallel processing started.",
    }
