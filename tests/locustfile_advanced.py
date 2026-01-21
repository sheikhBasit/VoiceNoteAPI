"""
Advanced Load Testing with Locust
Real-world scenario testing with multiple user behaviors

Includes:
- Multiple concurrent user profiles
- Different endpoint patterns
- Ramp-up and sustained load
- Performance metrics collection
- Failure tracking and debugging
"""

from locust import HttpUser, task, between, TaskSet, events
import random
import time
import json
from datetime import datetime


class APIMetrics:
    """Collect detailed metrics from load tests."""
    
    def __init__(self):
        self.response_times = []
        self.errors = []
        self.timestamps = []
    
    def record(self, response_time, error=None):
        self.response_times.append(response_time)
        self.timestamps.append(datetime.now())
        if error:
            self.errors.append(error)
    
    def percentile(self, p):
        """Calculate percentile response time."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * p / 100)
        return sorted_times[index]
    
    def report(self):
        """Generate report."""
        return {
            'count': len(self.response_times),
            'errors': len(self.errors),
            'min': min(self.response_times) if self.response_times else 0,
            'max': max(self.response_times) if self.response_times else 0,
            'avg': sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            'p50': self.percentile(50),
            'p90': self.percentile(90),
            'p99': self.percentile(99),
        }


# Global metrics
metrics = APIMetrics()


# ============================================================================
# USER BEHAVIORS
# ============================================================================

class NormalUserTasks(TaskSet):
    """Normal user behavior pattern."""
    
    @task(10)
    def get_notes(self):
        """List user notes (60% of traffic)."""
        with self.client.get("/api/notes", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")
    
    @task(5)
    def create_note(self):
        """Create a note (30% of traffic)."""
        payload = {
            "title": f"Note {random.randint(1, 1000)}",
            "transcript": "Sample transcript for testing" * 10,
        }
        with self.client.post("/api/notes", json=payload, catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")
    
    @task(3)
    def ask_ai(self):
        """Ask AI assistant (10% of traffic)."""
        payload = {
            "query": "What was the main topic?",
            "note_id": random.randint(1, 100),
        }
        with self.client.post("/api/ai/ask", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")


class PowerUserTasks(TaskSet):
    """Power user: heavy API usage."""
    
    @task(15)
    def get_notes_paginated(self):
        """Fetch notes with pagination."""
        page = random.randint(1, 10)
        with self.client.get(f"/api/notes?page={page}&limit=50", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")
    
    @task(10)
    def search_notes(self):
        """Search across notes."""
        query = random.choice(["task", "meeting", "reminder", "important"])
        with self.client.get(f"/api/notes/search?q={query}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")
    
    @task(8)
    def get_tasks(self):
        """Get tasks."""
        with self.client.get("/api/tasks", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")


class BurstUserTasks(TaskSet):
    """Burst user: sudden spike in traffic."""
    
    @task(20)
    def rapid_api_calls(self):
        """Make rapid API calls."""
        endpoints = [
            "/api/notes",
            "/api/tasks",
            "/api/users/profile",
        ]
        endpoint = random.choice(endpoints)
        with self.client.get(endpoint, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")


# ============================================================================
# USER TYPES
# ============================================================================

class NormalUser(HttpUser):
    """Normal usage pattern."""
    tasks = [NormalUserTasks]
    wait_time = between(1, 3)


class PowerUser(HttpUser):
    """Heavy usage pattern."""
    tasks = [PowerUserTasks]
    wait_time = between(0.5, 2)


class BurstUser(HttpUser):
    """Burst traffic pattern."""
    tasks = [BurstUserTasks]
    wait_time = between(0.1, 0.5)


# ============================================================================
# EVENT HANDLERS FOR METRICS COLLECTION
# ============================================================================

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Record every request for detailed analysis."""
    metrics.record(response_time, error=exception)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate report when test stops."""
    print("\n" + "="*80)
    print("LOAD TEST COMPLETE - FINAL METRICS")
    print("="*80)
    
    report = metrics.report()
    print(f"Total Requests: {report['count']}")
    print(f"Total Errors: {report['errors']}")
    print(f"Error Rate: {(report['errors']/report['count']*100) if report['count'] > 0 else 0:.2f}%")
    print(f"\nResponse Time Distribution (ms):")
    print(f"  Min:   {report['min']:.2f}ms")
    print(f"  P50:   {report['p50']:.2f}ms")
    print(f"  P90:   {report['p90']:.2f}ms")
    print(f"  P99:   {report['p99']:.2f}ms")
    print(f"  Max:   {report['max']:.2f}ms")
    print(f"  Avg:   {report['avg']:.2f}ms")
    print("="*80)
