from app.worker.celery_app import celery_app
from typing import List, Optional, Tuple, Dict
import json
import uuid
from app.core.audio import preprocess_audio_pipeline
from app.services.ai_service import AIService
from app.utils.ai_service_utils import AIServiceError
from app.services.calendar_service import CalendarService # New
from app.db.session import SessionLocal
from app.db.models import Note, Task, NoteStatus, Priority, User
import os
from datetime import datetime, timedelta
import time
import redis
from app.utils.json_logger import JLogger
from pydub import AudioSegment
from app.services.billing_service import BillingService
import requests
import tempfile

# Redis sync client for workers
try:
    _redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    if _redis_url.startswith("redis://") or _redis_url.startswith("rediss://"):
        redis_client = redis.from_url(_redis_url)
    else:
        # Fallback for memory:// or other testing schemes
        redis_client = None
except Exception:
    redis_client = None

def broadcast_ws_update(user_id: str, event_type: str, data: any):
    """Publish a real-time update to the WebSocket manager via Redis."""
    payload = {
        "user_id": user_id,
        "type": event_type,
        "data": data,
        "timestamp": int(time.time() * 1000)
    }
    if redis_client:
        try:
            redis_client.publish(f"user_updates_{user_id}", json.dumps(payload))
        except Exception as e:
            JLogger.warning("Failed to publish WS update to Redis", error=str(e))

@celery_app.task(name="ping_task")
def ping_task(message: str):
    """Simple task for testing Celery connectivity."""
    return {"status": "pong", "message": message, "timestamp": time.time()}

@celery_app.task(bind=True, name="process_voice_note_pipeline")
def note_process_pipeline(self, note_id: str, local_file_path: str, user_role: str, document_uris: Optional[List] = None, image_uris: Optional[List] = None, languages: Optional[List] = None, stt_model: str = "nova"):
    db = SessionLocal()
    ai_service = AIService()
    
    # Initialize these variables for cleanup in finally/except blocks
    is_storage_key = not local_file_path.startswith("uploads/")
    actual_local_path = local_file_path
    note_owner_id = None # Initialize for broadcast_ws_update in case of early failure

    try:
        # 1. Update status to PROCESSING
        JLogger.info("Worker: Starting note processing pipeline", note_id=note_id, user_role=user_role)
        db.query(Note).filter(Note.id == note_id).update({"status": NoteStatus.PROCESSING})
        db.commit()
        
        # Notify UI immediately
        note_owner_id = db.query(Note.user_id).filter(Note.id == note_id).scalar()
        if note_owner_id:
            broadcast_ws_update(note_owner_id, "NOTE_STATUS", {"note_id": note_id, "status": "PROCESSING"})

        # 2. Preprocess (Offloading from Android for battery/speed)
        broadcast_ws_update(note_owner_id, "PIPELINE_STEP", {"note_id": note_id, "step": "PREPROCESSING", "message": "Cleaning up audio and reducing noise..."})
        
        # New: MinIO/Storage Key awareness
        is_storage_key = not local_file_path.startswith("uploads/")
        actual_local_path = local_file_path
        
        if is_storage_key:
            from app.services.storage_service import StorageService
            storage_service = StorageService()
            local_tmp_path = os.path.join(tempfile.gettempdir(), f"storage_{note_id}.wav")
            storage_service.download_file(local_file_path, local_tmp_path)
            actual_local_path = local_tmp_path
            JLogger.info("Worker: Downloaded file from MinIO", note_id=note_id, storage_key=local_file_path)

        # WAIT for file to be ready (Docker volume sync/flush lag)
        max_waits = 10
        wait_count = 0
        while wait_count < max_waits:
            if os.path.exists(actual_local_path) and os.path.getsize(actual_local_path) > 0:
                break
            JLogger.info("Worker: File is empty or missing, waiting for sync...", path=actual_local_path, attempt=wait_count)
            time.sleep(1)
            wait_count += 1

        # Robustness Check: If local file is still gone or empty, attempt recovery if possible
        if not os.path.exists(actual_local_path) or os.path.getsize(actual_local_path) == 0:
            JLogger.warning("Local file missing or empty in worker after wait, attempting recovery", note_id=note_id, path=actual_local_path)
            note = db.query(Note).filter(Note.id == note_id).first()
            if note and note.raw_audio_url:
                # If it's a URL (http), try to download it
                if note.raw_audio_url.startswith("http"):
                    try:
                        response = requests.get(note.raw_audio_url, timeout=30)
                        if response.status_code == 200:
                            os.makedirs(os.path.dirname(actual_local_path), exist_ok=True)
                            with open(actual_local_path, "wb") as f:
                                f.write(response.content)
                            JLogger.info("Successfully recovered audio from URL", note_id=note_id, url=note.raw_audio_url)
                    except Exception as e:
                        JLogger.error("Failed to recover audio from URL", note_id=note_id, error=str(e))
                elif not os.path.exists(actual_local_path):
                    # It was a local path but is still missing
                    raise FileNotFoundError(f"Local file {actual_local_path} missing in worker for note {note_id}")
            else:
                raise FileNotFoundError(f"Local file {actual_local_path} missing or empty and no recovery URL for {note_id}")

        processed_path = preprocess_audio_pipeline(actual_local_path)

        # 3. Update audio_url with processed path (as a local URL)
        audio_url = f"/{processed_path}"

        # 4. AI Analysis (Whisper STT -> Llama 3.1 LLM)
        JLogger.info("Worker: Running AI analysis", note_id=note_id)
        broadcast_ws_update(note_owner_id, "PIPELINE_STEP", {"note_id": note_id, "step": "SUMMARIZING", "message": "AI is transcribing and summarizing your audio..."})
        
        # Fetch user profile for personalization and timezone context
        note = db.query(Note).filter(Note.id == note_id).first()
        user = note.user if note else None
        user_instr = user.system_prompt if user else ""
        user_jargons = user.jargons if user else []
        user_timezone = user.timezone if user else "UTC"  # NEW: Get user timezone
        
        analysis = ai_service.run_full_analysis_sync(
            processed_path, 
            user_role, 
            languages=languages,
            stt_model=stt_model,
            user_instruction=user_instr, 
            jargons=user_jargons,
            note_created_at=note.timestamp,  # NEW: Pass note creation timestamp
            user_timezone=user_timezone  # NEW: Pass user timezone for temporal context
        )
        JLogger.info("Worker: AI analysis complete", note_id=note_id, tasks_found=len(analysis.tasks))
        broadcast_ws_update(note_owner_id, "PIPELINE_STEP", {"note_id": note_id, "step": "TASK_EXTRACTION", "message": f"Found {len(analysis.tasks)} actionable tasks. Extracting details..."})

        # 5. Generate Vector Embedding for Semantic Search
        broadcast_ws_update(note_owner_id, "PIPELINE_STEP", {"note_id": note_id, "step": "VECTORIZING", "message": "Generating semantic vectors for intelligent search..."})
        embedding = ai_service.generate_embedding_sync(analysis.summary)

        # 6. Update Database with AI Results
        note = db.query(Note).filter(Note.id == note_id).first()
        note.title = analysis.title
        note.summary = analysis.summary
        
        # Save transcripts from meta
        transcripts = analysis.metadata.get("all_transcripts", {})
        if "deepgram" in transcripts:
            note.transcript_deepgram = transcripts["deepgram"]
        if "groq" in transcripts:
            note.transcript_groq = transcripts["groq"]
        
        # Handle fallback for primary if not in dict
        if stt_model == "whisper" and not note.transcript_groq:
            note.transcript_groq = analysis.transcript
        elif stt_model == "nova" and not note.transcript_deepgram:
            note.transcript_deepgram = analysis.transcript

        note.transcript_android = analysis.transcript # Global fallback
        note.audio_url = audio_url
        note.embedding = embedding
        note.tags = analysis.tags # NEW: Save AI generated tags
        note.embedding_version = 1 # Initial cache version
        note.status = NoteStatus.DONE
        broadcast_ws_update(note_owner_id, "PIPELINE_STEP", {"note_id": note_id, "step": "SAVING_NOTE", "message": "Saving note insights and generated tasks..."})
        
        # 7. Monetization Logic (Standout Strategy)
        try:
            # Use RAW audio for duration calculation as requested
            raw_audio = AudioSegment.from_file(local_file_path)
            duration_seconds = raw_audio.duration_seconds
            
            billing = BillingService(db)
            success = billing.charge_usage(
                user_id=note.user_id,
                description=f"AI Transcription & Analysis ({duration_seconds:.1f}s)",
                ref_id=note_id,
                audio_duration=duration_seconds
            )
            
            # Update user cache stats for note count
            user = db.query(User).filter(User.id == note.user_id).first()
            if user:
                from sqlalchemy.orm.attributes import flag_modified
                if not user.usage_stats:
                    user.usage_stats = {"total_audio_minutes": 0.0, "total_notes": 0, "total_tasks": 0, "last_usage_at": None}
                
                user.usage_stats["total_notes"] = user.usage_stats.get("total_notes", 0) + 1
                user.usage_stats["total_tasks"] = user.usage_stats.get("total_tasks", 0) + len(analysis.tasks)
                flag_modified(user, "usage_stats")
                db.commit()

            if not success:
               JLogger.warning("Insufficient funds or ledger failure for note processing", user_id=note.user_id, note_id=note_id)
            else:
               JLogger.info("Usage charged successfully", user_id=note.user_id, duration_s=duration_seconds)
               
        except Exception as e:
            JLogger.error("Failed to process charging logic", error=str(e))

        # 8. Map & Save Tasks with Smart Actions
        from app.services.action_generator import ActionGenerator
        
        extracted_tasks = []
        for t_data in analysis.tasks:
            # Extract action metadata from LLM response
            actions_metadata = t_data.get("actions", {}) if isinstance(t_data, dict) else {}
            suggested_actions = {}
            
            # Generate Google Search action
            if "google_search" in actions_metadata:
                suggested_actions["google_search"] = ActionGenerator.generate_google_search(
                    actions_metadata["google_search"]["query"]
                )
            
            # Generate Email action
            if "email" in actions_metadata:
                email_data = actions_metadata["email"]
                suggested_actions["email"] = ActionGenerator.generate_email_draft(
                    to=email_data.get("to", ""),
                    name=email_data.get("name", ""),
                    subject=email_data.get("subject", ""),
                    body=email_data.get("body", "")
                )
            
            # Generate WhatsApp action
            if "whatsapp" in actions_metadata:
                wa_data = actions_metadata["whatsapp"]
                suggested_actions["whatsapp"] = ActionGenerator.generate_whatsapp_message(
                    phone=wa_data.get("phone", ""),
                    name=wa_data.get("name", ""),
                    message=wa_data.get("message", "")
                )
            
            # Generate Map action
            if "map" in actions_metadata:
                map_data = actions_metadata["map"]
                suggested_actions["map"] = ActionGenerator.generate_map_link(
                    location=map_data.get("location", ""),
                    query=map_data.get("query", "")
                )

            # Generate AI Prompt action
            if "ai_prompt" in actions_metadata:
                ai_data = actions_metadata["ai_prompt"]
                suggested_actions["ai_prompt"] = ActionGenerator.generate_ai_prompt(
                    model=ai_data.get("model", "chatgpt"),
                    task_description=t_data.get("description") if isinstance(t_data, dict) else t_data.description,
                    context=note.summary or "",
                    custom_prompt=ai_data.get("prompt")
                )
            
            new_task = Task(
                id=str(uuid.uuid4()),
                user_id=note.user_id,
                note_id=note_id,
                title=t_data.get("title") or t_data.get("description", "Task")[:100],
                description=t_data["description"] if isinstance(t_data, dict) else t_data.description,
                priority=getattr(Priority, t_data["priority"] if isinstance(t_data, dict) else t_data.priority, Priority.MEDIUM),
                deadline=t_data["deadline"] if isinstance(t_data, dict) else t_data.deadline,
                suggested_actions=suggested_actions  # NEW: Add smart actions
            )
            db.add(new_task)
            extracted_tasks.append({
                "title": new_task.title,
                "description": new_task.description,
                "deadline": new_task.deadline
            })

        db.commit()

        # 8. PROACTIVE CONFLICT DETECTION (Requirement: Standout Strategy)
        broadcast_ws_update(note_owner_id, "PIPELINE_STEP", {"note_id": note_id, "step": "FINALIZING", "message": "Checking for calendar conflicts and finalizing tasks..."})
        user = db.query(Note).filter(Note.id == note_id).first().user
        if user and extracted_tasks:
            # NEW: Parallel Conflict Detection (Speed Optimization)
            from concurrent.futures import ThreadPoolExecutor
            
            def check_schedule():
                events = CalendarService.get_user_events(user.id)
                return ai_service.detect_conflicts_sync(
                    analysis.summary, 
                    [str(e.get('title', '')) for e in events], 
                    context_type="schedule"
                )
            
            def check_notes():
                similar_notes = db.query(Note).filter(
                    Note.user_id == user.id,
                    Note.id != note_id,
                    Note.is_deleted == False
                ).order_by(
                    Note.embedding.cosine_distance(embedding)
                ).limit(5).all()
                
                return ai_service.detect_conflicts_sync(
                    analysis.summary, 
                    [f"Title: {n.title}\nSummary: {n.summary}" for n in similar_notes], 
                    context_type="previous_notes"
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_schedule = executor.submit(check_schedule)
                future_notes = executor.submit(check_notes)
                
                schedule_conflicts = future_schedule.result()
                note_conflicts = future_notes.result()

            # Combine and notify
            all_conflicts = [
                {"type": "SCHEDULE", **c} for c in schedule_conflicts
            ] + [
                {"type": "FACTUAL", **c} for c in note_conflicts
            ]

            for conflict in all_conflicts:
                # Get device token
                device_token = "mock_token"
                if user.authorized_devices:
                    device_token = user.authorized_devices[0].get("biometric_token", "mock_token")
                
                msg_prefix = "📅 Schedule" if conflict["type"] == "SCHEDULE" else "⚠️ Factual"
                send_push_notification.delay(
                    device_token,
                    title=f"{msg_prefix} Conflict Alert!",
                    body=f"{conflict['explanation']} (Fact: {conflict['fact']} vs {conflict['conflict']})",
                    data={"type": "CONFLICT", "conflict": conflict}
                )

        JLogger.info("Worker: Note processing pipeline finished successfully", note_id=note_id)
        
        # Cleanup local file on SUCCESS
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
            
        return {"status": "success", "note_id": note_id, "conflicts_found": len(conflicts) if 'conflicts' in locals() else 0}

    except AIServiceError as e:
        JLogger.warning("Worker: AI Service Error (Likely silent or invalid audio)", note_id=note_id, error=str(e))
        db.query(Note).filter(Note.id == note_id).update({
            "status": NoteStatus.DONE,
            "summary": f"Note processed but no speech was detected: {str(e)}",
            "title": "Empty Note"
        })
        db.commit()
        broadcast_ws_update(note_owner_id, "NOTE_STATUS", {"note_id": note_id, "status": "DONE", "message": str(e)})

    except Exception as exc:
        JLogger.exception("Worker: Note processing pipeline failed", note_id=note_id)
        db.rollback()
        
        # Determine if we should cleanup on final failure
        if self.request.retries >= self.max_retries:
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
                
        self.retry(exc=exc, countdown=60) 
    finally:
        db.close()


@celery_app.task(name="process_task_image_pipeline")
def process_task_image_pipeline(task_id: str, local_path: str, filename: str):
    """Process task multimedia (images/documents)."""
    db = SessionLocal()
    try:
        # Detect if image or document
        is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        
        # Ensure uploads directory exists
        if not os.path.exists("uploads"):
            os.makedirs("uploads")
            
        # Move/Ensure file is in permanent storage if it was temp
        # For now, we assume local_path is already in 'uploads/' or a valid persistence layer
        # If it was a temp file, we should have moved it. 
        # CAUTION: If local_path is /tmp/..., we must move it.
        # But based on typical usage, let's assume valid persistent path.

        if is_image:
            from PIL import Image
            
            # Generate Thumbnail
            try:
                with Image.open(local_path) as img:
                    img.thumbnail((300, 300))
                    thumb_path = f"{os.path.splitext(local_path)[0]}_thumb.jpg"
                    img.save(thumb_path, "JPEG", quality=70)
                    JLogger.info("Thumbnail generated", path=thumb_path)
            except Exception as e:
                JLogger.warning("Thumbnail generation failed", error=str(e))
            
            # Update DB
            secure_url = f"/{local_path}" # Relative URL
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                # Appending secure_url. Frontend can deduce thumb url by appending _thumb.jpg
                task.image_urls = (task.image_urls or []) + [secure_url]
        else:
            secure_url = f"/{local_path}"
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.document_urls = (task.document_urls or []) + [secure_url]

        db.commit()
    except Exception as e:
        db.rollback()
        JLogger.error("Worker: Multimedia processing failed", task_id=task_id, error=str(e))
    finally:
        db.close()
        # DO NOT DELETE local_path here, as it is the permanent file served by StaticFiles



@celery_app.task(name="check_upcoming_tasks")
def check_upcoming_tasks():
    """Check for tasks due within 24 hours and send notifications."""
    db = SessionLocal()
    try:
        # Define "Due Soon" as within the next 24 hours
        now_ms = int(time.time() * 1000)
        soon_ms = now_ms + (24 * 60 * 60 * 1000)

        # Query tasks that are: 
        # 1. Not done 2. Not deleted 3. Deadline is between now and 24h from now
        upcoming_tasks = db.query(Task).filter(
            Task.is_done == False,
            Task.is_deleted == False,
            Task.deadline >= now_ms,
            Task.deadline <= soon_ms
        ).all()

        from zoneinfo import ZoneInfo
        
        for task in upcoming_tasks:
            user = db.query(User).filter(User.id == task.user_id).first()
            
            if not user or not user.authorized_devices:
                continue
            
            # Use the first available token for now
            device_token = user.authorized_devices[0].get("biometric_token")
            if not device_token:
                continue
            
            # Use user's local time to check work hours
            user_tz = ZoneInfo(user.timezone or "UTC")
            now_user = datetime.fromtimestamp(time.time(), tz=user_tz)
            current_hour = now_user.hour
            
            # Check if current time is within user's work hours
            is_work_time = user.work_start_hour <= current_hour < user.work_end_hour
            
            # Also check if today is a work day
            # now_user.isoweekday() returns 1 (Mon) - 7 (Sun)
            is_work_day = now_user.isoweekday() in (user.work_days or [1,2,3,4,5])

            # Only notify if it's work hours/day OR if it's a High Priority emergency
            if (is_work_time and is_work_day) or task.priority == Priority.HIGH:
                send_push_notification.delay(
                    device_token,
                    title="Task Due Soon! ⏰",
                    body=f"Reminder: '{task.description}' is due in less than 24 hours.",
                    data={"task_id": task.id, "type": "DEADLINE_REMINDER"}
                )
    except Exception as e:
        JLogger.error("Worker: Upcoming tasks check failed", error=str(e))
    finally:
        db.close()

@celery_app.task(name="send_push_notification")
def send_push_notification(device_token: str, title: str, body: str, data: dict):
    """
    Integration point with Firebase Cloud Messaging (FCM).
    """
    from app.services.notification_service import NotificationService
    try:
        NotificationService.initialize()
        NotificationService.send_to_token(device_token, title, body, data)
    except Exception as e:
        JLogger.error("Push Notification Failed in Worker", device_token=device_token, error=str(e))


@celery_app.task(name="hard_delete_expired_records")
def hard_delete_expired_records():
    """
    30-Day Rule: Hard delete any records where is_deleted=True 
    and updated_at is older than 30 days.
    
    This task runs daily at 3 AM UTC via Celery Beat.
    """
    db = SessionLocal()
    try:
        # Calculate 30 days ago in milliseconds
        thirty_days_ms = 30 * 24 * 60 * 60 * 1000
        cutoff_time = int(time.time() * 1000) - thirty_days_ms
        
        # Track deletion counts
        deleted_counts = {"users": 0, "notes": 0, "tasks": 0}
        
        # Step 1: Find soft-deleted tasks older than 30 days
        expired_tasks = db.query(Task).filter(
            Task.is_deleted == True,
            Task.updated_at < cutoff_time
        ).all()
        
        for task in expired_tasks:
            db.delete(task)
            deleted_counts["tasks"] += 1
        
        # Step 2: Find soft-deleted notes older than 30 days
        expired_notes = db.query(Note).filter(
            Note.is_deleted == True,
            Note.updated_at < cutoff_time
        ).all()
        
        for note in expired_notes:
            # Delete associated tasks first (cascade may not handle soft-deleted)
            db.query(Task).filter(Task.note_id == note.id).delete()
            db.delete(note)
            deleted_counts["notes"] += 1
        
        # Step 3: Find soft-deleted users older than 30 days
        expired_users = db.query(User).filter(
            User.is_deleted == True,
            User.deleted_at < cutoff_time
        ).all()
        
        for user in expired_users:
            # Delete all user's notes and tasks
            user_notes = db.query(Note).filter(Note.user_id == user.id).all()
            for note in user_notes:
                db.query(Task).filter(Task.note_id == note.id).delete()
                db.delete(note)
            db.delete(user)
            deleted_counts["users"] += 1
        
        db.commit()
        
        total_deleted = sum(deleted_counts.values())
        if total_deleted > 0:
            JLogger.info("30-Day Cleanup Complete", deleted=deleted_counts)
        else:
            JLogger.info("30-Day Cleanup: No records found")
        
        return {"status": "success", "deleted": deleted_counts}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error in 30-day cleanup: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="reset_api_key_limits")
def reset_api_key_limits():
    """
    Reset API key rate limits daily.
    
    This task runs daily at midnight UTC via Celery Beat.
    """
    db = SessionLocal()
    try:
        from sqlalchemy import text
        
        # Reset rate limits for all active API keys
        result = db.execute(text("""
            UPDATE api_keys 
            SET 
                rate_limit_remaining = 1000,
                error_count = CASE WHEN error_count < 10 THEN 0 ELSE error_count END,
                updated_at = EXTRACT(EPOCH FROM NOW()) * 1000
            WHERE is_active = TRUE
            RETURNING id
        """))
        
        reset_count = result.rowcount
        db.commit()
        
        print(f"🔄 API Key Limits Reset: {reset_count} keys updated")
        return {"status": "success", "keys_reset": reset_count}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error resetting API key limits: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="rotate_to_backup_key")
def rotate_to_backup_key(service_name: str, failed_key_id: str, error_reason: str):
    """
    Rotate to backup API key when primary fails.
    
    Called when an API key hits rate limits or returns errors.
    Must complete within 1 second as per requirements.
    """
    db = SessionLocal()
    try:
        from sqlalchemy import text
        
        # Mark the failed key
        db.execute(text("""
            UPDATE api_keys 
            SET 
                error_count = error_count + 1,
                last_error_at = EXTRACT(EPOCH FROM NOW()) * 1000,
                is_active = CASE 
                    WHEN :error_reason LIKE '%rate limit%' THEN is_active
                    WHEN error_count >= 5 THEN FALSE
                    ELSE is_active
                END
            WHERE id = :key_id
        """), {"key_id": failed_key_id, "error_reason": error_reason.lower()})
        
        # Get the next available key
        result = db.execute(text("""
            SELECT id, api_key FROM api_keys
            WHERE service_name = :service
              AND is_active = TRUE
              AND id != :failed_key
            ORDER BY priority ASC, error_count ASC
            LIMIT 1
        """), {"service": service_name, "failed_key": failed_key_id})
        
        next_key = result.fetchone()
        db.commit()
        
        if next_key:
            print(f"🔄 Rotated to backup key for {service_name}")
            return {"status": "rotated", "new_key_id": str(next_key[0])}
        else:
            print(f"⚠️ No backup keys available for {service_name}")
            return {"status": "no_backup", "service": service_name}
            
    except Exception as e:
        db.rollback()
        print(f"❌ Error rotating API key: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
@celery_app.task(name="analyze_note_semantics_task")
def analyze_note_semantics_task(note_id: str):
    """Refined background task for deep analysis of note semantics."""
    db = SessionLocal()
    ai_service = AIService()
    try:
        note = db.query(Note).filter(Note.id == note_id).first()
        if not note:
            return {"error": "Note not found"}

        transcript = note.transcript
        if not transcript:
            return {"error": "No transcript available"}

        user = note.user if note else None
        user_role = user.primary_role.name if user else "GENERIC"
        user_instr = user.system_prompt if user else ""
        user_jargons = user.jargons if user else []
        
        # Call AI service
        JLogger.info("Worker: Running semantic analysis", note_id=note_id)
        analysis = ai_service.semantic_analysis_sync(
            transcript, 
            user_role,
            jargons=user_jargons,
            personal_instruction=user_instr
        )
        
        # Save result to JSONB field for caching
        note.semantic_analysis = {
            "sentiment": analysis.sentiment,
            "tone": analysis.tone,
            "patterns": analysis.hidden_patterns,
            "suggested_questions": analysis.suggested_questions,
            "analyzed_at": int(time.time() * 1000)
        }
        db.commit()
        
        JLogger.info("Worker: Semantic analysis complete", note_id=note_id)
        return {"status": "success", "note_id": note_id}
    except Exception as e:
        JLogger.error("Worker: Semantic analysis failed", note_id=note_id, error=str(e))
        db.rollback()
        raise
    finally:
        db.close()

@celery_app.task(name="process_ai_query_task")
def process_ai_query_task(note_id: str, question: str, user_id: str):
    """Handles background AI Q&A for specific notes."""
    db = SessionLocal()
    ai_service = AIService()
    try:
        note = db.query(Note).filter(Note.id == note_id).first()
        if not note:
            return {"error": "Note not found"}

        transcript = note.transcript
        user_role = note.user.primary_role.name if note.user else "GENERIC"
        
        # Generate Answer
        response = ai_service.llm_brain_sync(transcript, user_role, question)
        
        # Append to ai_responses history
        new_resp = {
            "question": question,
            "answer": response.summary if hasattr(response, 'summary') else str(response),
            "timestamp": int(time.time() * 1000)
        }
        
        history = list(note.ai_responses) if note.ai_responses else []
        history.append(new_resp)
        note.ai_responses = history
        db.commit()
        
        # Notify UI of AI Response
        if note.user_id:
            broadcast_ws_update(note.user_id, "AI_RESPONSE", new_resp)
        
        return {"status": "success", "response": new_resp}
    except Exception as e:
        JLogger.error("Worker: AI query processing failed", note_id=note_id, error=str(e))
        db.rollback()
        raise
    finally:
        db.close()

@celery_app.task(name="generate_note_embeddings_task", bind=True, max_retries=3)
def generate_note_embeddings_task(self, note_id: str):
    """Regenerates embeddings when note content changes significantly."""
    db = SessionLocal()
    ai_service = AIService()
    try:
        note = db.query(Note).filter(Note.id == note_id).first()
        if not note:
            return {"error": "Note not found"}

        # Combine title and summary for better semantic representation
        text_to_embed = f"{note.title}\n{note.summary}"
        embedding = ai_service.generate_embedding_sync(text_to_embed)
        
        note.embedding = embedding
        note.embedding_version += 1
        db.commit()
        
        return {"status": "success", "version": note.embedding_version}
    except Exception as e:
        JLogger.error("Worker: Embedding generation failed", note_id=note_id, error=str(e))
        db.rollback()
        self.retry(exc=e, countdown=30)
    finally:
        db.close()

@celery_app.task(name="generate_productivity_report_task")
def generate_productivity_report_task():
    """Scheduled task to generate weekly reports for all active users."""
    db = SessionLocal()
    from app.services.analytics_service import AnalyticsService
    from app.db.models import User, UserRole
    analytics = AnalyticsService()
    try:
        # 1. Get all active users
        users = db.query(User).filter(User.is_deleted == False).all()
        
        for user in users:
            try:
                # 2. Get productivity pulse for the week
                pulse = analytics.get_productivity_pulse(db, user.id)
                
                # 3. Format a summary message
                report_body = f"Hello {user.name or 'User'}! Here is your weekly productivity pulse:\n\n"
                report_body += f"📊 Active Notes: {pulse.get('total_notes_this_week', 0)}\n"
                report_body += f"✅ Tasks Completed: {pulse.get('tasks_completed', 0)}\n"
                report_body += f"💡 Insight: {pulse.get('suggestion', 'Keep up the great work!')}"
                
                # 4. Trigger pushing notification (Real-world: Email or Push)
                device_token = None
                if user.authorized_devices:
                    device_token = user.authorized_devices[0].get("biometric_token")
                
                if device_token:
                    send_push_notification.delay(
                        device_token,
                        title="📈 Your Weekly Pulse is Ready!",
                        body="Tap to see your productivity summary for the last 7 days.",
                        data={"type": "WEEKLY_REPORT", "pulse": pulse}
                    )
            except Exception as e:
                JLogger.error(f"Failed to generate report for user {user.id}", error=str(e))
                continue
                
        return {"status": "success", "users_processed": len(users)}
    finally:
        db.close()

@celery_app.task(name="sync_external_service_task")
def sync_external_service_task(note_id: str, service_name: str, user_id: str):
    """
    Background worker for third-party integrations (Google Calendar, Notion).
    Requirement: "Sync to Google Calendar or Export to Notion should be background tasks"
    """
    db = SessionLocal()
    try:
        if service_name.lower() == "google_calendar":
            # Logic for calendar sync (using existing CalendarService)
            pass
        elif service_name.lower() == "notion":
            # Future expansion for Notion export
            pass
            
        return {"status": "success", "service": service_name, "note_id": note_id}
    finally:
        db.close()

from celery.signals import worker_ready

@worker_ready.connect
def warmup_worker(sender, **kwargs):
    """Warm up AI models on worker startup."""
    try:
        JLogger.info("Worker ready: Warming up AI embedding model...")
        service = AIService()
        service._get_local_embedding_model()
        JLogger.info("Worker warmup complete.")
    except Exception as e:
        JLogger.error("Worker warmup failed", error=str(e))
