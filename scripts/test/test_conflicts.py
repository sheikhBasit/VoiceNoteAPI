import time

class CalendarService:
    @staticmethod
    def detect_conflicts(tasks, events):
        conflicts = []
        for task in tasks:
            deadline = task.get("deadline")
            if not deadline:
                continue
            for event in events:
                if event["start_time"] <= deadline <= event["end_time"]:
                    conflicts.append({
                        "task": task["description"],
                        "conflicting_event": event["title"]
                    })
        return conflicts

def test_conflicts():
    tasks = [{"description": "Finish Report", "deadline": 1000}]
    events = [{"title": "Meeting", "start_time": 500, "end_time": 1500}]
    
    conflicts = CalendarService.detect_conflicts(tasks, events)
    if len(conflicts) == 1 and conflicts[0]["conflicting_event"] == "Meeting":
        print("✅ Conflict Detection Logic Verified")
    else:
        print("❌ Conflict Detection Logic Failed")

if __name__ == "__main__":
    test_conflicts()
