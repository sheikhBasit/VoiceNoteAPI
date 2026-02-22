from app.utils.json_logger import JLogger
import time

logs_received = []

def test_listener(log):
    logs_received.append(log)

JLogger.add_listener(test_listener)

JLogger.info("Test log for verification", source="verification_script")
JLogger.error("Error log for verification", code=500)

time.sleep(0.1)

print(f"Logs received by listener: {len(logs_received)}")
for log in logs_received:
    print(f" - {log['level']}: {log['message']} (source: {log.get('source', 'N/A')})")

JLogger.remove_listener(test_listener)
