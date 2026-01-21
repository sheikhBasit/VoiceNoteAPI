from .celery_app import celery_app
import cloudinary.uploader
from app.core.audio import preprocess_audio_pipeline
from app.services.ai_service import AIService
from app.services.cloudinary_service import CloudinaryService
from app.db.session import SessionLocal
from app.db.models import Note, Task, NoteStatus, Priority
import os
from datetime import datetime, timedelta
import time

@celery_app.task(name="process_voice_note_pipeline", bind=True, max_retries=3)
def process_voice_note_pipeline(self, note_id: str, local_file_path: str, user_role: str):
    db = SessionLocal()
    ai_service = AIService()
    
    try:
        # 1. Update status to PROCESSING
        db.query(Note).filter(Note.id == note_id).update({"status": NoteStatus.PENDING})
        db.commit()

        # 2. Preprocess (Offloading from Android for battery/speed)
        processed_path = preprocess_audio_pipeline(local_file_path)

        # 3. Upload to Cloudinary (Stores both raw and processed if needed)
        upload_result = cloudinary.uploader.upload(processed_path, resource_type="video")
        audio_url = upload_result.get("secure_url")

        # 4. AI Analysis (Whisper STT -> Llama 3.1 LLM)
        # Inherits logic from Android's AiRepository.processConversationChunks
        analysis = ai_service.run_full_analysis(processed_path, user_role)

        # 5. Generate Vector Embedding for Semantic Search
        embedding = ai_service.generate_embedding(analysis.summary)

        # 6. Update Database with AI Results
        note = db.query(Note).filter(Note.id == note_id).first()
        note.title = analysis.title
        note.summary = analysis.summary
        note.transcript_groq = analysis.transcript  # Store with engine identifier
        note.audio_url = audio_url
        note.embedding = embedding
        note.status = NoteStatus.DONE
        
        # 7. Map & Save Tasks (Replacing Task.kt logic)
        for t_data in analysis.tasks:
            new_task = Task(
                note_id=note_id,
                description=t_data.description,
                priority=getattr(Priority, t_data.priority, Priority.MEDIUM),
                deadline=t_data.deadline
            )
            db.add(new_task)

        db.commit()
        return {"status": "success", "note_id": note_id}

    except Exception as exc:
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
