from .celery_app import celery_app
import cloudinary.uploader
from app.core.audio import preprocess_audio_pipeline
from app.services.ai_service import AIService
from app.services.cloudinary_service import CloudinaryService
from app.services.calendar_service import CalendarService # New
from app.db.session import SessionLocal
from app.db.models import Note, Task, NoteStatus, Priority
import os
from datetime import datetime, timedelta
import time
from app.utils.json_logger import JLogger
@celery_app.task(name="ping_task")
def ping_task(message: str):
    """Simple task for testing Celery connectivity."""
    return {"status": "pong", "message": message, "timestamp": time.time()}

@celery_app.task(name="process_voice_note_pipeline", bind=True, max_retries=3)
def process_voice_note_pipeline(self, note_id: str, local_file_path: str, user_role: str):
    db = SessionLocal()
    ai_service = AIService()
    
    try:
        # 1. Update status to PROCESSING
        JLogger.info("Worker: Starting note processing pipeline", note_id=note_id, user_role=user_role)
        db.query(Note).filter(Note.id == note_id).update({"status": NoteStatus.PROCESSING})
        db.commit()

        # 2. Preprocess (Offloading from Android for battery/speed)
        processed_path = preprocess_audio_pipeline(local_file_path)

        # 3. Upload to Cloudinary (Stores both raw and processed if needed)
        upload_result = cloudinary.uploader.upload(processed_path, resource_type="video")
        audio_url = upload_result.get("secure_url")

        # 4. AI Analysis (Whisper STT -> Llama 3.1 LLM)
        # Inherits logic from Android's AiRepository.processConversationChunks
        JLogger.info("Worker: Running AI analysis", note_id=note_id)
        analysis = ai_service.run_full_analysis(processed_path, user_role)
        JLogger.info("Worker: AI analysis complete", note_id=note_id, tasks_found=len(analysis.tasks))

        # 5. Generate Vector Embedding for Semantic Search
        embedding = ai_service.generate_embedding(analysis.summary)

        # 6. Update Database with AI Results
        note = db.query(Note).filter(Note.id == note_id).first()
        note.title = analysis.title
        note.summary = analysis.summary
        note.transcript_groq = analysis.transcript
        note.transcript_deepgram = analysis.transcript # Propagate for consistency
        note.transcript_android = analysis.transcript  # Propagate for consistency
        note.audio_url = audio_url
        note.embedding = embedding
        note.status = NoteStatus.DONE
        
        # 7. Map & Save Tasks (Replacing Task.kt logic)
        extracted_tasks = []
        for t_data in analysis.tasks:
            new_task = Task(
                note_id=note_id,
                description=t_data["description"] if isinstance(t_data, dict) else t_data.description,
                priority=getattr(Priority, t_data["priority"] if isinstance(t_data, dict) else t_data.priority, Priority.MEDIUM),
                deadline=t_data["deadline"] if isinstance(t_data, dict) else t_data.deadline
            )
            db.add(new_task)
            extracted_tasks.append({
                "description": new_task.description,
                "deadline": new_task.deadline
            })

        db.commit()

        # 8. PROACTIVE CONFLICT DETECTION (Requirement: Standout Strategy)
        user = db.query(Note).filter(Note.id == note_id).first().user
        if user and extracted_tasks:
            events = CalendarService.get_user_events(user.id)

            conflicts = CalendarService.detect_conflicts(extracted_tasks, events)
            
            for conflict in conflicts:
                send_push_notification.delay(
                    user.token or "mock_token",
                    title="📅 Schedule Conflict Alert!",
                    body=f"Target: {conflict['task']} conflicts with '{conflict['conflicting_event']}'",
                    data={"type": "CONFLICT", "conflict": conflict}
                )

        JLogger.info("Worker: Note processing pipeline finished successfully", note_id=note_id)
        return {"status": "success", "note_id": note_id, "conflicts_found": len(conflicts) if 'conflicts' in locals() else 0}

    except Exception as exc:
        JLogger.exception("Worker: Note processing pipeline failed", note_id=note_id)
        db.rollback()
        # Handle Failover Key Rotation or API errors
        self.retry(exc=exc, countdown=60) 
    finally:
        db.close()
        if os.path.exists(local_file_path):
            os.remove(local_file_path)


@celery_app.task(name="process_task_image_pipeline")
def process_task_image_pipeline(task_id: str, local_path: str, filename: str):
    """Process and upload task multimedia (images/documents) to Cloudinary."""
    db = SessionLocal()
    cloud_service = CloudinaryService()
    try:
        # 1. Detect if image or document
        is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        
        if is_image:
            # Compresses and uploads (non-async wrapper)
            secure_url = cloud_service.upload_compressed_image(local_path, task_id)
            # Add to image_urls JSONB array
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.image_urls = task.image_urls + [secure_url]
        else:
            # Standard upload for docs (non-async wrapper)
            secure_url = cloud_service.upload_audio(local_path, f"doc_{task_id}")
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.document_urls = task.document_urls + [secure_url]

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error processing multimedia for task {task_id}: {str(e)}")
    finally:
        db.close()
        if os.path.exists(local_path):
            os.remove(local_path)


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
        upcoming_tasks = db.query(Task).join(Note).filter(
            Task.is_done == False,
            Task.is_deleted == False,
            Task.deadline >= now_ms,
            Task.deadline <= soon_ms
        ).all()

        current_hour = datetime.now().hour
        
        for task in upcoming_tasks:
            user = db.query(Task).filter(Task.note_id == task.note_id).first().note.user
            
            if not user or not user.token:
                continue
            
            # Check if current time is within user's work hours
            is_work_time = user.work_start_hour <= current_hour < user.work_end_hour
            
            # Only notify if it's work hours OR if it's a High Priority emergency
            if is_work_time or task.priority == Priority.HIGH:
                send_push_notification.delay(
                    user.token,
                    title="Task Due Soon! ⏰",
                    body=f"Reminder: '{task.description}' is due in less than 24 hours.",
                    data={"task_id": task.id, "type": "DEADLINE_REMINDER"}
                )
    except Exception as e:
        print(f"Error checking upcoming tasks: {str(e)}")
    finally:
        db.close()

@celery_app.task(name="send_push_notification")
def send_push_notification(device_token: str, title: str, body: str, data: dict):
    """
    Integration point with Firebase Cloud Messaging (FCM).
    """
    try:
        # Here you would call the Firebase Admin SDK
        # firebase_admin.messaging.send(...)
        print(f"Sending Notification to {device_token}: {title} - {body}")
        print(f"Data: {data}")
    except Exception as e:
        print(f"Error sending push notification: {str(e)}")


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
        from app.db.models import User
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
            print(f"🗑️  30-Day Cleanup Complete: {deleted_counts}")
        else:
            print("✅ 30-Day Cleanup: No expired records found")
        
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
