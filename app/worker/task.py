from .celery_app import celery_app
import cloudinary.uploader
from app.core.audio import preprocess_audio_pipeline
from app.services.ai_service import AIService 
from app.db.session import SessionLocal
from app.db.models import Note, Task, NoteStatus
import os

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
        note.transcript = analysis.transcript
        note.audio_url = audio_url
        note.embedding = embedding
        note.status = NoteStatus.DONE
        
        # 7. Map & Save Tasks (Replacing Task.kt logic)
        for t_data in analysis.tasks:
            new_task = Task(
                note_id=note_id,
                description=t_data.description,
                priority=t_data.priority,
                deadline=t_data.deadline,
                google_prompt=t_data.google_prompt,
                ai_prompt=t_data.ai_prompt
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