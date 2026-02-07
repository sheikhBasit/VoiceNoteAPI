import time


def trace_import(module_name):
    print(f"[{time.time()}] Starting import of {module_name}...")
    try:
        __import__(module_name)
        print(f"[{time.time()}] Finished import of {module_name}.")
    except Exception as e:
        print(f"[{time.time()}] ERROR importing {module_name}: {e}")


print("--- Detailed Import Trace ---")
trace_import("app.db.models")
trace_import("app.core.audio")
trace_import("app.services.ai_service")
trace_import("app.services.calendar_service")
trace_import("app.services.billing_service")
trace_import("app.worker.task")
print("--- Trace Complete ---")
