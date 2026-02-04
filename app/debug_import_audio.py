import time
import sys
import os

def trace_import(module_name):
    print(f"[{time.ctime()}] Importing {module_name}...")
    start = time.time()
    try:
        __import__(module_name)
        end = time.time()
        print(f"[{time.ctime()}] SUCCESS: {module_name} (took {end-start:.2f}s)")
    except Exception as e:
        print(f"[{time.ctime()}] FAILED: {module_name} - {e}")

print("--- Starting Detailed Sub-Import Trace for app.core.audio ---")
trace_import("librosa")
trace_import("soundfile")
trace_import("numpy")
trace_import("noisereduce")
trace_import("pydub")
trace_import("scipy")
trace_import("app.utils.audio_quality_analyzer")
print("--- Sub-Import Trace Finished ---")
