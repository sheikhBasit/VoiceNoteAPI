import time


def trace_import(module_name):
    print(f"[{time.ctime()}] Importing {module_name}...")
    start = time.time()
    try:
        if "." in module_name:
            # Handle from X import Y
            parts = module_name.split(" ")
            if parts[0] == "from":
                # from X import Y
                mod = __import__(parts[1], fromlist=[parts[3]])
            else:
                __import__(module_name)
        else:
            __import__(module_name)
        end = time.time()
        print(f"[{time.ctime()}] SUCCESS: {module_name} (took {end-start:.2f}s)")
    except Exception as e:
        print(f"[{time.ctime()}] FAILED: {module_name} - {e}")


print("--- Starting Detailed Import Trace ---")
trace_import("typing")
trace_import("from app.worker.celery_app import celery_app")
trace_import("json")
trace_import("uuid")
trace_import("from app.core.audio import preprocess_audio_pipeline")
trace_import("from app.services.ai_service import AIService")
trace_import("from app.services.calendar_service import CalendarService")
trace_import("from app.db.session import SessionLocal")
trace_import("from app.db.models import Note, Task, NoteStatus, Priority, User")
trace_import("os")
trace_import("from datetime import datetime, timedelta")
trace_import("time")
trace_import("redis")
trace_import("from app.utils.json_logger import JLogger")
trace_import("from pydub import AudioSegment")
trace_import("from app.services.billing_service import BillingService")
print("--- Import Trace Finished ---")
