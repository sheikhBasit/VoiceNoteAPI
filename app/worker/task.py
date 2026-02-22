import json
import os
import tempfile
import time
import uuid
from datetime import datetime
from typing import Any, List, Optional

import redis
import requests
try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None
    print("Warning: pydub not available, audio processing will fail.")


from celery.signals import worker_ready

from app.core.audio import preprocess_audio_pipeline
from app.db.models import Note, NoteStatus, Priority, Task, User
from app.db.session import SessionLocal
from app.services.ai_service import AIService
from app.services.billing_service import BillingService
from app.services.image_service import ImageService
from app.utils.ai_service_utils import AIServiceError
from app.utils.json_logger import JLogger
from app.worker.celery_app import celery_app

# Redis sync client for workers
try:
    _redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    if _redis_url.startswith("redis://") or _redis_url.startswith("rediss://"):
        redis_client = redis.from_url(
            _redis_url, 
            max_connections=20, 
            decode_responses=True,
            health_check_interval=30
        )
    else:
        # Fallback for memory:// or other testing schemes
        redis_client = None
except Exception:
    redis_client = None


def broadcast_team_update(team_id: str, event_type: str, data: Any, trigger_id: str = None):
    """Publish a real-time update for a team via Redis (SSE compatible)."""
    payload = {
        "type": event_type,
        "data": data,
        "trigger_id": trigger_id or str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
    }
    if redis_client:
        try:
            redis_client.publish(f"team:{team_id}", json.dumps(payload))
        except Exception as e:
            JLogger.warning("Failed to publish team update to Redis", error=str(e))


def broadcast_user_update(user_id: str, event_type: str, data: Any, trigger_id: str = None):
    """Publish a real-time update for a specific user via Redis (SSE compatible)."""
    payload = {
        "type": event_type,
        "data": data,
        "trigger_id": trigger_id or str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
    }
    if redis_client:
        try:
            # SSE Broadcaster listens on user:{user_id}
            redis_client.publish(f"user:{user_id}", json.dumps(payload))
            # Legacy WS manager listens on user_updates_{user_id}
            redis_client.publish(f"user_updates_{user_id}", json.dumps(payload))
        except Exception as e:
            JLogger.warning("Failed to publish user update to Redis", error=str(e))


def broadcast_ws_update(user_id: str, event_type: str, data: Any):
    """Legacy helper, redirects to broadcast_user_update."""
    broadcast_user_update(user_id, event_type, data)


@celery_app.task(name="ping_task")
def ping_task(message: str):
    """Simple task for testing Celery connectivity."""
    return {"status": "pong", "message": message, "timestamp": time.time()}


@celery_app.task(bind=True, name="process_voice_note_pipeline", max_retries=3)
def note_process_pipeline(
    self,
    note_id: str,
    local_file_path: str,
    user_role: str,
    document_uris: Optional[List] = None,
    image_uris: Optional[List] = None,
    languages: Optional[List] = None,
    stt_model: str = "nova",
):
    # Initialize these variables for cleanup in finally/except blocks
    is_storage_key = not local_file_path.startswith("uploads/")
    actual_local_path = local_file_path
    note_owner_id = None  # Initialize for broadcast_ws_update in case of early failure
    temp_files_to_clean = []

    with SessionLocal() as db:
        ai_service = AIService()
        start_time = time.time()  # New: Track total duration
        try:
            # 1. Update status to PROCESSING
            JLogger.info(
                "Worker: Starting note processing pipeline",
                note_id=note_id,
                user_role=user_role,
            )
            db.query(Note).filter(Note.id == note_id).update(
                {"status": NoteStatus.PROCESSING}
            )
            db.commit()

            # Notify UI immediately
            note = db.query(Note).filter(Note.id == note_id).first()
            if note and note.user_id:
                note_owner_id = note.user_id
                broadcast_user_update(
                    note.user_id,
                    "NOTE_STATUS",
                    {"note_id": note_id, "status": "PROCESSING"},
                )
                if note.team_id:
                    broadcast_team_update(
                        note.team_id,
                        "NOTE_STATUS",
                        {"note_id": note_id, "status": "PROCESSING", "user_id": note.user_id},
                    )

            # 2. Preprocess (Offloading from Android for battery/speed)
            broadcast_ws_update(
                note_owner_id,
                "PIPELINE_STEP",
                {
                    "note_id": note_id,
                    "step": "PREPROCESSING",
                    "message": "Cleaning up audio and reducing noise...",
                },
            )

            # New: MinIO/Storage Key awareness
            is_storage_key = not local_file_path.startswith("uploads/")
            actual_local_path = local_file_path

            if is_storage_key:
                from app.services.storage_service import StorageService

                storage_service = StorageService()
                local_tmp_path = os.path.join(
                    tempfile.gettempdir(), f"storage_{note_id}.wav"
                )
                storage_service.download_file(local_file_path, local_tmp_path)
                actual_local_path = local_tmp_path
                temp_files_to_clean.append(actual_local_path)
                JLogger.info(
                    "Worker: Downloaded file from MinIO",
                    note_id=note_id,
                    storage_key=local_file_path,
                )

            # WAIT for file to be ready (Docker volume sync/flush lag)
            max_waits = 10
            wait_count = 0
            while wait_count < max_waits:
                if (
                    os.path.exists(actual_local_path)
                    and os.path.getsize(actual_local_path) > 0
                ):
                    break
                JLogger.info(
                    "Worker: File is empty or missing, waiting for sync...",
                    path=actual_local_path,
                    attempt=wait_count,
                )
                time.sleep(1)
                wait_count += 1

            # Robustness Check: If local file is still gone or empty, attempt recovery if possible
            if (
                not os.path.exists(actual_local_path)
                or os.path.getsize(actual_local_path) == 0
            ):
                JLogger.warning(
                    "Local file missing or empty in worker after wait, attempting recovery",
                    note_id=note_id,
                    path=actual_local_path,
                )
                note = db.query(Note).filter(Note.id == note_id).first()
                if note and note.raw_audio_url:
                    # If it's a URL (http), try to download it
                    if note.raw_audio_url.startswith("http"):
                        try:
                            response = requests.get(note.raw_audio_url, timeout=30)
                            if response.status_code == 200:
                                os.makedirs(
                                    os.path.dirname(actual_local_path), exist_ok=True
                                )
                                with open(actual_local_path, "wb") as f:
                                    f.write(response.content)
                                JLogger.info(
                                    "Successfully recovered audio from URL",
                                    note_id=note_id,
                                    url=note.raw_audio_url,
                                )
                        except Exception as e:
                            JLogger.error(
                                "Failed to recover audio from URL",
                                note_id=note_id,
                                error=str(e),
                            )
                    elif not os.path.exists(actual_local_path):
                        # It was a local path but is still missing
                        raise FileNotFoundError(
                            f"Local file {actual_local_path} missing in worker for note {note_id}"
                        )
                else:
                    raise FileNotFoundError(
                        f"Local file {actual_local_path} missing or empty and no recovery URL for {note_id}"
                    )

            processed_path = preprocess_audio_pipeline(actual_local_path)
            temp_files_to_clean.append(processed_path)

            # 3. Update audio_url with processed path (as a local URL)
            audio_url = f"/{processed_path}"

            # 4. Transcribe Audio
            JLogger.info("Worker: Transcribing audio", note_id=note_id)
            transcript, engine, detected_langs, all_transcripts = ai_service.transcribe_with_failover_sync(
                processed_path, languages=languages, stt_model=stt_model
            )

            # 5. RAG: Fetch Historical Context
            JLogger.info("Worker: Fetching historical context...", note_id=note_id)
            from app.services.rag_service import RAGService
            context_notes = RAGService.get_context_for_transcript(
                db, note.user_id, transcript, exclude_note_id=note_id
            )

            # 6. AI Analysis with Context
            JLogger.info("Worker: Running LLM analysis with context", note_id=note_id)
            # Fetch user profile for personalization and timezone context
            note = db.query(Note).filter(Note.id == note_id).first() # Re-fetch in case it was updated
            user = note.user if note else None
            user_instr = user.system_prompt if user else ""
            user_jargons = user.jargons if user else []
            user_timezone = user.timezone if user else "UTC"

            analysis = ai_service.llm_brain_sync(
                transcript,
                user_role,
                user_instruction=user_instr,
                jargons=user_jargons,
                note_created_at=note.timestamp,
                user_timezone=user_timezone,
                context_notes=context_notes,
            )
            analysis.metadata = {
                "engine": engine,
                "languages": detected_langs,
                "all_transcripts": all_transcripts,
            }
            JLogger.info(
                "Worker: AI analysis complete",
                note_id=note_id,
                tasks_found=len(analysis.tasks),
            )
            broadcast_ws_update(
                note_owner_id,
                "PIPELINE_STEP",
                {
                    "note_id": note_id,
                    "step": "TASK_EXTRACTION",
                    "message": f"Found {len(analysis.tasks)} actionable tasks. Extracting details...",
                },
            )

            # 5. Generate Vector Embedding for Semantic Search
            broadcast_ws_update(
                note_owner_id,
                "PIPELINE_STEP",
                {
                    "note_id": note_id,
                    "step": "VECTORIZING",
                    "message": "Generating semantic vectors for intelligent search...",
                },
            )
            embedding = ai_service.generate_embedding_sync(analysis.summary)

            # NEW: Semantic Linking (Similarity > 0.85 => Distance < 0.15)
            # Find related notes to link automatically
            related_links = []
            try:
                related_notes = (
                    db.query(Note.id, Note.title)
                    .filter(
                        Note.user_id == note.user_id,
                        Note.id != note_id,
                        Note.embedding.cosine_distance(embedding) < 0.15,
                        Note.is_deleted == False
                    )
                    .limit(5)
                    .all()
                )
                related_links = [
                    {"id": r.id, "title": r.title, "type": "semantic_similarity"} 
                    for r in related_notes
                ]
                JLogger.info(f"Found {len(related_links)} related notes for linking", note_id=note_id)
            except Exception as e:
                JLogger.warning(f"Semantic linking failed: {e}", note_id=note_id)

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

            note.audio_url = audio_url
            note.embedding = embedding
            note.tags = analysis.tags
            
            # Save related links in semantic_analysis (or merge with existing)
            current_analysis = note.semantic_analysis or {}
            current_analysis["related_notes"] = related_links
            current_analysis["business_leads"] = getattr(analysis, "business_leads", [])
            note.semantic_analysis = current_analysis
            
            # Save processing duration
            duration_ms = int((time.time() - start_time) * 1000)
            note.processing_time_ms = duration_ms
            JLogger.info(f"Worker: Processing duration: {duration_ms}ms", note_id=note_id)

            note.embedding_version = 1
            note.status = NoteStatus.DONE
            broadcast_ws_update(
                note_owner_id,
                "PIPELINE_STEP",
                {
                    "note_id": note_id,
                    "step": "SAVING_NOTE",
                    "message": "Saving note insights and generated tasks...",
                },
            )

            # 7. Monetization Logic
            try:
                raw_audio = AudioSegment.from_file(local_file_path)
                duration_seconds = raw_audio.duration_seconds

                billing = BillingService(db)
                billing.charge_usage(
                    user_id=note.user_id,
                    description=f"AI Transcription & Analysis ({duration_seconds:.1f}s)",
                    ref_id=note_id,
                    audio_duration=duration_seconds,
                )

                # Update user cache stats
                user = db.query(User).filter(User.id == note.user_id).first()
                if user:
                    from sqlalchemy.orm.attributes import flag_modified
                    if not user.usage_stats:
                        user.usage_stats = {
                            "total_audio_minutes": 0.0,
                            "total_notes": 0,
                            "total_tasks": 0,
                            "last_usage_at": None,
                        }
                    user.usage_stats["total_notes"] = user.usage_stats.get("total_notes", 0) + 1
                    user.usage_stats["total_tasks"] = user.usage_stats.get("total_tasks", 0) + len(analysis.tasks)
                    flag_modified(user, "usage_stats")
                    db.commit()
            except Exception as e:
                JLogger.critical("CRITICAL: Failed to process charging logic for completed note",
                                note_id=note_id, user_id=note.user_id, error=str(e))

            # 8. Map & Save Tasks with Smart Actions
            from app.services.action_suggestion_service import ActionSuggestionService
            extracted_tasks = []
            for t_data in analysis.tasks:
                # Helper to normalize access
                is_dict = isinstance(t_data, dict)
                raw_title = t_data.get("title") if is_dict else getattr(t_data, "title", None)
                raw_desc = t_data.get("description") if is_dict else getattr(t_data, "description", None)
                raw_prio = t_data.get("priority") if is_dict else getattr(t_data, "priority", "MEDIUM")
                raw_deadline = t_data.get("deadline") if is_dict else getattr(t_data, "deadline", None)
                if not raw_deadline and is_dict: 
                    raw_deadline = t_data.get("due_date")

                final_title = raw_title or (raw_desc if raw_desc else "Task")[:100]
                final_desc = raw_desc or raw_title or "No description provided."

                # GHOST TASK PREVENTION: Check for duplicates
                existing_task = db.query(Task).filter(
                    Task.note_id == note_id,
                    Task.title == final_title,
                    Task.deadline == raw_deadline
                ).first()

                if existing_task:
                    JLogger.info(f"Worker: Skipping duplicate task '{final_title}'", note_id=note_id)
                    continue

                actions_metadata = t_data.get("actions", {}) if is_dict else getattr(t_data, "actions", {})
                suggested_actions = {}

                if "google_search" in actions_metadata:
                    suggested_actions["google_search"] = ActionSuggestionService.generate_google_search(
                        actions_metadata["google_search"]["query"]
                    )
                if "email" in actions_metadata:
                    email_data = actions_metadata["email"]
                    suggested_actions["email"] = ActionSuggestionService.generate_email_draft(
                        to=email_data.get("to", ""),
                        name=email_data.get("name", ""),
                        subject=email_data.get("subject", ""),
                        body=email_data.get("body", ""),
                    )
                if "whatsapp" in actions_metadata:
                    wa_data = actions_metadata["whatsapp"]
                    suggested_actions["whatsapp"] = ActionSuggestionService.generate_whatsapp_message(
                        phone=wa_data.get("phone", ""),
                        name=wa_data.get("name", ""),
                        message=wa_data.get("message", ""),
                    )
                if "call" in actions_metadata:
                    call_data = actions_metadata["call"]
                    suggested_actions["call"] = ActionSuggestionService.generate_call_link(
                        phone=call_data.get("phone", ""),
                        name=call_data.get("name", ""),
                    )
                if "map" in actions_metadata:
                    map_data = actions_metadata["map"]
                    suggested_actions["map"] = ActionSuggestionService.generate_map_link(
                        location=map_data.get("location", ""),
                        query=map_data.get("query", ""),
                    )
                if "ai_prompt" in actions_metadata:
                    ai_data = actions_metadata["ai_prompt"]
                    suggested_actions["ai_prompt"] = ActionSuggestionService.generate_ai_prompt(
                        model=ai_data.get("model", "chatgpt"),
                        task_description=final_desc,
                        context=note.summary or "",
                        custom_prompt=ai_data.get("prompt"),
                    )

                from app.services.task_service import TaskService
                task_service = TaskService(db)
                new_task = task_service.create_task_with_deduplication(
                    user_id=note.user_id,
                    title=final_title,
                    description=final_desc,
                    note_id=note_id,
                    deadline=raw_deadline,
                    priority=getattr(
                        Priority,
                        raw_prio,
                        Priority.MEDIUM,
                    ),
                    assigned_entities=t_data.get("assigned_entities", []) if is_dict else getattr(t_data, "assigned_entities", []),
                    suggested_actions=suggested_actions
                )

                if note.team_id:
                    broadcast_team_update(
                        note.team_id,
                        "TASK_CREATED",
                        {
                            "task_id": new_task.id,
                            "note_id": note_id,
                            "title": new_task.title,
                            "priority": new_task.priority.value,
                        },
                    )

                extracted_tasks.append(
                    {
                        "title": new_task.title,
                        "description": new_task.description,
                        "deadline": new_task.deadline,
                    }
                )
            db.commit()

            # 9. PROACTIVE CONFLICT DETECTION
            broadcast_ws_update(
                note_owner_id,
                "PIPELINE_STEP",
                {
                    "note_id": note_id,
                    "step": "FINALIZING",
                    "message": "Checking for calendar conflicts and finalizing tasks...",
                },
            )
            all_conflicts = []
            user = db.query(Note).filter(Note.id == note_id).first().user
            if user and extracted_tasks:
                # Only Note-based Factual Conflicts remain
                similar_notes = db.query(Note).filter(
                    Note.user_id == user.id, Note.id != note_id, Note.is_deleted.is_(False)
                ).order_by(Note.embedding.cosine_distance(embedding)).limit(5).all()
                
                note_conflicts = ai_service.detect_conflicts_sync(
                    analysis.summary,
                    [f"Title: {n.title}\nSummary: {n.summary}" for n in similar_notes],
                    context_type="previous_notes",
                )

                all_conflicts = [{"type": "FACTUAL", **c} for c in note_conflicts]
                
                # Persist conflicts for UI display
                note.conflicts = all_conflicts

                for conflict in all_conflicts:
                    device_token = "mock_token"
                    if user.authorized_devices:
                        device_token = user.authorized_devices[0].get("biometric_token", "mock_token")
                    msg_prefix = "⚠️ Factual"
                    send_push_notification.delay(
                        device_token,
                        title=f"{msg_prefix} Conflict Alert!",
                        body=f"{conflict['explanation']} (Fact: {conflict['fact']} vs {conflict['conflict']})",
                        data={"type": "CONFLICT", "conflict": conflict},
                    )

            JLogger.info("Worker: Note processing pipeline finished successfully", note_id=note_id)

            return {
                "status": "success",
                "note_id": note_id,
                "conflicts_found": len(all_conflicts),
            }

        except AIServiceError as e:
            JLogger.warning("Worker: AI Service Error", note_id=note_id, error=str(e))
            db.query(Note).filter(Note.id == note_id).update(
                {
                    "status": NoteStatus.DONE,
                    "summary": f"Note processed but no speech was detected: {str(e)}",
                    "title": "Empty Note",
                }
            )
            db.commit()
            broadcast_ws_update(note_owner_id, "NOTE_STATUS", {"note_id": note_id, "status": "DONE", "message": str(e)})

        except (ConnectionError, TimeoutError, OSError, IOError) as exc:
            # Transient errors — worth retrying
            JLogger.exception("Worker: Transient error in pipeline, retrying", note_id=note_id)
            db.rollback()
            self.retry(exc=exc, countdown=60)

        except Exception as exc:
            # Non-transient errors (validation, permission, data issues) — don't retry
            JLogger.exception("Worker: Note processing pipeline failed permanently", note_id=note_id)
            db.rollback()
            db.query(Note).filter(Note.id == note_id).update(
                {"status": NoteStatus.DELAYED, "summary": f"Processing failed: {str(exc)[:200]}"}
            )
            db.commit()
        finally:
            # CLEANUP: Ensure all temp files are removed regardless of success/error
            for f_path in temp_files_to_clean:
                try:
                    if os.path.exists(f_path):
                        os.remove(f_path)
                except Exception as cleanup_err:
                    JLogger.warning(f"Failed to cleanup temp file: {f_path}", error=str(cleanup_err))
            
            # Special case for local_file_path if it was a direct upload (not storage key)
            if not is_storage_key and os.path.exists(local_file_path):
                 try:
                     os.remove(local_file_path)
                 except Exception:
                     pass


@celery_app.task(name="process_task_image_pipeline")
def process_task_image_pipeline(task_id: str, local_path: str, filename: str):
    """Process task multimedia (images/documents)."""
    with SessionLocal() as db:
        try:
            # Detect if image or document
            is_image = filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))

            # Ensure uploads directory exists
            if not os.path.exists("uploads"):
                os.makedirs("uploads")

            # Move/Ensure file is in permanent storage if it was temp
            # For now, we assume local_path is already in 'uploads/' or a valid persistence layer
            # If it was a temp file, we should have moved it.
            # CAUTION: If local_path is /tmp/..., we must move it.
            # But based on typical usage, let's assume valid persistent path.

            if is_image:
                # PROFESSIONAL IMAGE OPTIMIZATION
                optimized_path = f"{os.path.splitext(local_path)[0]}_ready.jpg"
                thumb_path = f"{os.path.splitext(local_path)[0]}_thumb.jpg"

                # Compress main image
                if ImageService.process_image(local_path, optimized_path):
                    # Replace original with optimized one for serving
                    os.replace(optimized_path, local_path)

                # Generate Thumbnail
                ImageService.generate_thumbnail(local_path, thumb_path)

                # Update DB
                secure_url = f"/{local_path}"  # Relative URL for StaticFiles
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    # Appending to image_uris (JSONB)
                    current_uris = list(task.image_uris or [])
                    current_uris.append(secure_url)
                    task.image_uris = current_uris
            else:
                secure_url = f"/{local_path}"
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    current_uris = list(task.document_uris or [])
                    current_uris.append(secure_url)
                    task.document_uris = current_uris

            db.commit()
        except Exception as e:
            db.rollback()
            JLogger.error(
                "Worker: Multimedia processing failed", task_id=task_id, error=str(e)
            )
            raise


@celery_app.task(name="check_upcoming_tasks")
def check_upcoming_tasks():
    """
    Check for tasks due within the next hour and send notifications.
    Runs every minute via Celery Beat.
    """
    with SessionLocal() as db:
        try:
            now_ms = int(time.time() * 1000)
            # We only notify tasks due in the next 60 minutes to keep it relevant for a 1-minute scan
            soon_ms = now_ms + (60 * 60 * 1000)

            # Query tasks that are:
            # 1. Not done 2. Not deleted 3. Notified_at is null 4. Deadline is coming up
            from sqlalchemy.orm import joinedload
            upcoming_tasks = (
                db.query(Task)
                .options(joinedload(Task.user))
                .filter(
                    Task.is_done.is_(False),
                    Task.is_deleted.is_(False),
                    Task.notification_enabled.is_(True),
                    Task.notified_at.is_(None),
                    Task.deadline >= now_ms,
                    Task.deadline <= soon_ms,
                )
                .all()
            )

            from zoneinfo import ZoneInfo

            for task in upcoming_tasks:
                user = task.user

                if not user or not user.authorized_devices:
                    continue

                # Find a valid FCM token
                device_token = None
                for device in user.authorized_devices:
                    if device.get("biometric_token"):
                        device_token = device.get("biometric_token")
                        break

                if not device_token:
                    continue

                # User timezone logic
                try:
                    user_tz = ZoneInfo(user.timezone or "UTC")
                except Exception:
                    user_tz = ZoneInfo("UTC")

                now_user = datetime.fromtimestamp(time.time(), tz=user_tz)

                # Policy: Respect work hours unless HIGH priority
                is_work_time = user.work_start_hour <= now_user.hour < user.work_end_hour
                is_work_day = now_user.isoweekday() in (user.work_days or [1, 2, 3, 4, 5])

                if (is_work_time and is_work_day) or task.priority == Priority.HIGH:
                    send_push_notification.delay(
                        device_token,
                        f"Reminder: {task.title}",
                        f"Task due soon: {task.description[:50]}...",
                        {"task_id": task.id, "type": "task_deadline"},
                    )

                    # Mark as notified to prevent duplicate in next minute's scan
                    task.notified_at = now_ms
                    db.commit()

        except Exception as e:
            JLogger.error("Worker: Upcoming tasks check failed", error=str(e))


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
        JLogger.error(
            "Push Notification Failed in Worker",
            device_token=device_token,
            error=str(e),
        )


@celery_app.task(name="hard_delete_expired_records")
def hard_delete_expired_records():
    """
    30-Day Rule: Hard delete any records where is_deleted=True
    and updated_at is older than 30 days.
    """
    with SessionLocal() as db:
        try:
            # Calculate 30 days ago in milliseconds
            thirty_days_ms = 30 * 24 * 60 * 60 * 1000
            cutoff_time = int(time.time() * 1000) - thirty_days_ms

            # Track deletion counts
            deleted_counts = {"users": 0, "notes": 0, "tasks": 0}

            # Step 1: Bulk delete Tasks
            deleted_counts["tasks"] = db.query(Task).filter(
                Task.is_deleted.is_(True), Task.updated_at < cutoff_time
            ).delete(synchronize_session=False)
            
            # Step 2: Bulk delete Notes (and Cascade Tasks via DB FK)
            # Note: Since we have ON DELETE CASCADE in DB, deleting Note will delete Tasks.
            # But let's be explicit for safety if DB constraints vary.
            expired_notes_query = db.query(Note).filter(
                Note.is_deleted.is_(True), Note.updated_at < cutoff_time
            )
            # We can't rely on cascade in python-side bulk delete unless configured. 
            # Best practice is to let DB handle FK cascade.
            # Assuming DB has ON DELETE CASCADE configured in models.py (which it does)
            deleted_counts["notes"] = expired_notes_query.delete(synchronize_session=False)

            # Step 3: Bulk delete Users
            # Assuming DB ON DELETE CASCADE handles Notes/Tasks cleaning
            deleted_counts["users"] = db.query(User).filter(
                User.is_deleted.is_(True), User.deleted_at < cutoff_time
            ).delete(synchronize_session=False)

            db.commit()
            JLogger.info("Worker: Daily cleanup complete", **deleted_counts)
            return {"status": "success", "counts": deleted_counts}

        except Exception as e:
            db.rollback()
            JLogger.error("Worker: Cleanup failed", error=str(e))
            raise


@celery_app.task(name="reset_api_key_limits")
def reset_api_key_limits():
    """Reset API key rate limits daily."""
    with SessionLocal() as db:
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
            db.commit()
            return {"status": "success", "keys_reset": result.rowcount}
        except Exception as e:
            db.rollback()
            JLogger.error("Worker: API limits reset failed", error=str(e))
            raise


@celery_app.task(name="rotate_to_backup_key")
def rotate_to_backup_key(service_name: str, failed_key_id: str, error_reason: str):
    """Rotate to backup API key when primary fails."""
    with SessionLocal() as db:
        try:
            from sqlalchemy import text
            # Mark the failed key
            db.execute(
                text("""
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
            """),
                {"key_id": failed_key_id, "error_reason": error_reason.lower()},
            )
            # Get next best key
            result = db.execute(
                text("""
                SELECT id FROM api_keys
                WHERE service_name = :service AND is_active = TRUE AND id != :failed_key
                ORDER BY priority ASC, error_count ASC LIMIT 1
            """),
                {"service": service_name, "failed_key": failed_key_id},
            )
            next_key = result.fetchone()
            db.commit()
            return {"status": "success", "new_key_id": str(next_key[0]) if next_key else None}
        except Exception as e:
            db.rollback()
            JLogger.error("Worker: API key rotation failed", error=str(e))
            raise


@celery_app.task(name="analyze_note_semantics_task")
def analyze_note_semantics_task(note_id: str):
    """Refined background task for deep analysis of note semantics."""
    ai_service = AIService()
    with SessionLocal() as db:
        try:
            note = db.query(Note).filter(Note.id == note_id).first()
            if not note:
                return {"error": "Note not found"}

            transcript = note.transcript
            if not transcript:
                return {"error": "No transcript available"}

            user = note.user
            user_role = user.primary_role.name if user else "GENERIC"
            user_instr = user.system_prompt if user else ""
            user_jargons = user.jargons if user else []

            # Call AI service
            JLogger.info("Worker: Running semantic analysis", note_id=note_id)
            analysis = ai_service.semantic_analysis_sync(
                transcript, user_role, jargons=user_jargons, personal_instruction=user_instr
            )

            # Save result to JSONB field for caching
            note.semantic_analysis = {
                "sentiment": analysis.sentiment,
                "tone": analysis.tone,
                "patterns": analysis.hidden_patterns,
                "suggested_questions": analysis.suggested_questions,
                "analyzed_at": int(time.time() * 1000),
            }
            db.commit()

            JLogger.info("Worker: Semantic analysis complete", note_id=note_id)
            return {"status": "success", "note_id": note_id}
        except Exception as e:
            db.rollback()
            JLogger.error("Worker: Semantic analysis failed", note_id=note_id, error=str(e))
            raise


@celery_app.task(name="process_ai_query_task")
def process_ai_query_task(note_id: str, question: str, user_id: str):
    """Handles background AI Q&A for specific notes."""
    ai_service = AIService()
    with SessionLocal() as db:
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
                "answer": (
                    response.summary if hasattr(response, "summary") else str(response)
                ),
                "timestamp": int(time.time() * 1000),
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
            db.rollback()
            JLogger.error(
                "Worker: AI query processing failed", note_id=note_id, error=str(e)
            )
            raise


@celery_app.task(name="generate_note_embeddings_task", bind=True, max_retries=3)
def generate_note_embeddings_task(self, note_id: str):
    """Regenerates embeddings when note content changes significantly."""
    ai_service = AIService()
    with SessionLocal() as db:
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
            db.rollback()
            JLogger.error(
                "Worker: Embedding generation failed", note_id=note_id, error=str(e)
            )
            self.retry(exc=e, countdown=30)




@celery_app.task(name="generate_productivity_report_task")
def generate_productivity_report_task():
    """Scheduled task to generate weekly reports for all active users."""
    from app.db.models import User
    from app.services.analytics_service import AnalyticsService

    analytics = AnalyticsService()
    with SessionLocal() as db:
        try:
            # 1. Get all active users
            users = db.query(User).filter(User.is_deleted.is_(False)).all()

            for user in users:
                try:
                    # 2. Get productivity pulse for the week
                    pulse = analytics.get_productivity_pulse(db, user.id)

                    # 3. Format a summary message
                    report_body = f"Hello {user.name or 'User'}! Here is your weekly productivity pulse:\n\n"
                    report_body += (
                        f"📊 Active Notes: {pulse.get('total_notes_this_week', 0)}\n"
                    )
                    report_body += (
                        f"✅ Tasks Completed: {pulse.get('tasks_completed', 0)}\n"
                    )
                    report_body += (
                        f"💡 Insight: {pulse.get('suggestion', 'Keep up the great work!')}"
                    )

                    # 4. Trigger pushing notification (Real-world: Email or Push)
                    device_token = None
                    if user.authorized_devices:
                        device_token = user.authorized_devices[0].get("biometric_token")

                    if device_token:
                        send_push_notification.delay(
                            device_token,
                            title="📈 Your Weekly Pulse is Ready!",
                            body="Tap to see your productivity summary for the last 7 days.",
                            data={"type": "WEEKLY_REPORT", "pulse": pulse},
                        )
                except Exception as e:
                    JLogger.error(
                        f"Failed to generate report for user {user.id}", error=str(e)
                    )
                    continue

            return {"status": "success", "users_processed": len(users)}
        except Exception as e:
            JLogger.error("Weekly report task failed", error=str(e))
            raise


@celery_app.task(name="sync_external_service_task")
def sync_external_service_task(task_id: str, service_name: str, user_id: str):
    """
    Background worker for third-party integrations (Notion, Trello).
    Requirement: "Prepare a json draft... do not execute until user sends is_action_approved=True"
    """
    with SessionLocal() as db:
        try:
            from app.services.productivity_service import ProductivityService

            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return {"error": f"Task {task_id} not found"}

            task_data = {
                "title": task.title,
                "description": task.description,
                "deadline": task.deadline,
            }

            if service_name.lower() == "notion":
                ProductivityService.export_to_notion(user_id, task_data)
            elif service_name.lower() == "trello":
                ProductivityService.export_to_trello(user_id, task_data)

            return {"status": "success", "service": service_name, "task_id": task_id}
        except Exception as e:
            JLogger.error(f"External sync failed: {e}", task_id=task_id, service=service_name)
            return {"error": str(e)}


@celery_app.task(name="cleanup_expired_tokens_task")
def cleanup_expired_tokens_task():
    """
    Periodic task to clean up expired or revoked refresh tokens.
    Keeps the refresh_tokens table from growing indefinitely.
    """
    with SessionLocal() as db:
        try:
            now_ms = int(time.time() * 1000)
            # Delete tokens that are either revoked OR expired
            from app.db.models import RefreshToken
            deleted_count = db.query(RefreshToken).filter(
                (RefreshToken.expires_at < now_ms) | (RefreshToken.is_revoked == True)
            ).delete()
            db.commit()
            JLogger.info("Cleaned up expired/revoked refresh tokens", count=deleted_count)
            return {"status": "success", "deleted_count": deleted_count}
        except Exception as e:
            JLogger.error("Failed to cleanup refresh tokens", error=str(e))
            db.rollback()
            return {"error": str(e)}


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
