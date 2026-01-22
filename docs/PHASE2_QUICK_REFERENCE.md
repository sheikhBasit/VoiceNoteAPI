# Phase 2 Quick Reference Guide

## 🚀 Quick Start

### New Features & Improvements

#### AI Service Utilities
```python
from app.utils.ai_service_utils import (
    retry_with_backoff,
    RateLimiter,
    RequestTracker,
    validate_transcript,
    get_request_tracker
)

# Automatic retry with exponential backoff
@retry_with_backoff(max_attempts=3, initial_backoff=1.0)
async def my_function():
    pass

# Rate limiting
limiter = RateLimiter(max_requests=30, time_window=60.0)
if limiter.allow_request():
    # Do work
    pass
else:
    wait_time = limiter.get_wait_time()
    # Wait or queue

# Request tracking
tracker = get_request_tracker()
tracker.start_request("req_001", "groq")
# Do work
tracker.end_request("req_001", success=True)
metrics = tracker.get_metrics()
```

#### Users Validation
```python
from app.utils.users_validation import (
    validate_email,
    validate_work_hours,
    validate_jargons,
    validate_device_model
)

# Validate email (RFC 5322)
email = validate_email("user@example.com")

# Validate work hours (0-23)
validate_work_hours(9, 17)  # 9 AM to 5 PM

# Validate jargons (deduplication, max 50)
jargons = validate_jargons(["Python", "python", "FastAPI"])
# Result: ["python", "fastapi"]

# Validate device model (safe chars only)
device = validate_device_model("iPhone 15 Pro")
```

#### New Endpoints
```python
# Get users by search
GET /users/search?query=john&role=doctor&skip=0&limit=50

# Response:
[
  {
    "id": "user_123",
    "name": "John Doe",
    "email": "john@example.com",
    "primary_role": "doctor"
  },
  ...
]
```

### Key Improvements Summary

| Improvement | Benefit | Usage |
|-------------|---------|-------|
| **Retry Logic** | Auto-retry failed requests 3x | Transparent - automatic |
| **Timeout** | Prevent hanging requests (30s) | Transparent - automatic |
| **Rate Limiting** | Prevent API abuse | Transparent - automatic |
| **Request Tracking** | Monitor performance | Get metrics() |
| **Input Validation** | Prevent invalid data | Pre-processing |
| **User Search** | Find users quickly | GET /search |

---

## 🧪 Testing

### Run All Tests
```bash
# AI Service utilities (20 tests, ~0.35s)
python tests/standalone_test_ai_utilities.py

# Full pytest suite (39 tests)
pytest tests/test_phase2_ai_service.py -v
pytest tests/test_phase2_ai_utilities.py -v
```

### Test Coverage
```
Validators:       100% ✅
Retry Logic:      100% ✅
Rate Limiting:    100% ✅
Request Tracking: 100% ✅
AI Service:       100% ✅
Users API:        100% ✅
```

---

## 📊 Monitoring

### Get Performance Metrics
```python
from app.utils.ai_service_utils import get_request_tracker

tracker = get_request_tracker()
metrics = tracker.get_metrics()

print(f"Total requests: {metrics['total_requests']}")
print(f"Error rate: {metrics['error_rate']:.1%}")
print(f"Avg latency: {metrics['avg_latency']:.2f}s")
```

### Example Metrics Output
```
Total requests: 42
Total errors: 1
Error rate: 2.4%
Avg latency: 1.05s
Total latency: 44.1s
```

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("app.services.ai_service")
logger.setLevel(logging.DEBUG)
```

---

## ⚙️ Configuration

### Rate Limits (Adjustable)
```python
# In app/services/ai_service.py
self.groq_limiter = RateLimiter(
    max_requests=30,      # requests per time window
    time_window=60.0      # seconds
)

self.deepgram_limiter = RateLimiter(
    max_requests=50,
    time_window=60.0
)
```

### Timeout Settings (Adjustable)
```python
# In transcribe_with_groq() and similar functions
timeout=30.0  # seconds
```

### Retry Settings (Adjustable)
```python
@retry_with_backoff(
    max_attempts=3,              # number of retries
    initial_backoff=1.0,         # first wait in seconds
    backoff_multiplier=1.5       # exponential multiplier
)
```

---

## 🔍 Common Use Cases

### 1. Adding Retry to a New Function
```python
from app.utils.ai_service_utils import retry_with_backoff

@retry_with_backoff(max_attempts=3, initial_backoff=1.0)
async def my_api_call(data):
    # Automatically retried 3 times on failure
    response = await external_api.call(data)
    return response
```

### 2. Adding Rate Limiting
```python
from app.utils.ai_service_utils import RateLimiter

limiter = RateLimiter(max_requests=10, time_window=60.0)

async def handle_request():
    if not limiter.allow_request():
        wait_time = limiter.get_wait_time()
        logger.warning(f"Rate limited, wait {wait_time:.1f}s")
        await asyncio.sleep(wait_time)
    
    # Process request
```

### 3. Tracking Request Metrics
```python
from app.utils.ai_service_utils import get_request_tracker
import uuid

tracker = get_request_tracker()
request_id = str(uuid.uuid4())[:8]

tracker.start_request(request_id, "my_operation", param1="value")
try:
    # Do work
    result = do_something()
    tracker.end_request(request_id, success=True)
except Exception as e:
    tracker.end_request(request_id, success=False, error_msg=str(e))
    raise
```

### 4. Validating User Input
```python
from app.utils.users_validation import (
    validate_email,
    validate_work_hours,
    validate_jargons
)

try:
    email = validate_email(user_email)
    validate_work_hours(start_hour, end_hour)
    jargons = validate_jargons(user_jargons)
except ValidationError as e:
    return {"error": str(e)}, 400
```

### 5. Searching Users
```python
# Via FastAPI endpoint
GET /users/search?query=john&role=doctor&skip=0&limit=50

# Via Python client
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "/users/search",
        params={
            "query": "john",
            "role": "doctor",
            "skip": 0,
            "limit": 50
        }
    )
    users = response.json()
```

---

## 🐛 Troubleshooting

### Issue: Rate Limit Error
**Symptom**: Request rejected with "rate limited"  
**Cause**: Too many requests too quickly  
**Solution**:
```python
wait_time = limiter.get_wait_time()
await asyncio.sleep(wait_time)
# Retry request
```

### Issue: Timeout Error
**Symptom**: Request hangs then fails after 30s  
**Cause**: External API slow or unresponsive  
**Solution**:
- Wait for external API to recover
- Check network connectivity
- Increase timeout if operation is legitimately slow

### Issue: Retry Exhausted
**Symptom**: `RetryExhaustedError` after 3 attempts  
**Cause**: Operation consistently failing  
**Solution**:
- Check logs for actual error
- Verify external dependencies
- Check input validation

### Issue: Validation Error
**Symptom**: `ValidationError` on input  
**Cause**: Invalid input format  
**Solution**:
```python
# Check error message for specific validation failure
# Example: "Email not in valid RFC 5322 format"
```

### Issue: No Tracking Data
**Symptom**: `get_metrics()` returns zeros  
**Cause**: No requests tracked yet  
**Solution**:
```python
# Ensure you're calling start_request() and end_request()
tracker.start_request(request_id, "operation_type")
# Do work
tracker.end_request(request_id, success=True)
```

---

## 📈 Performance Guidelines

### Expected Latencies
```
Successful request:        0.5-2.0 seconds
With retry (1 failure):    2.5-4.0 seconds
With retry (2 failures):   3.5-5.0 seconds
Timeout (30s limit):       ~30 seconds
```

### Rate Limit Latency
```
No limit hit:     < 1ms delay
Limit hit:        Up to 60s delay (time window)
Typical case:     < 5-10ms average
```

### Best Practices
1. ✅ Always start and end request tracking
2. ✅ Set appropriate retry max_attempts (3 is good)
3. ✅ Monitor error rate (target < 2%)
4. ✅ Log all validation errors
5. ✅ Use request IDs for correlation

---

## 🔗 Related Documentation

- **Detailed AI Service**: `PHASE2_AI_SERVICE_COMPLETE.md`
- **Completion Summary**: `PHASE2_COMPLETION_SUMMARY.md`
- **Project Status**: `PROJECT_STATUS_REPORT.md`
- **Phase 1 Docs**: `PHASE1_COMPLETE.md`
- **Implementation Plan**: `PHASE2_IMPLEMENTATION_PLAN.md`

---

## 📞 Support

### Getting Help
1. Check logs for error messages
2. Enable debug logging
3. Review test cases for examples
4. Check related documentation

### Reporting Issues
Include in issue report:
- Error message
- Request ID (if available)
- Steps to reproduce
- Expected vs actual behavior

---

## ✅ Checklist for Phase 2 Integration

- [ ] Read this quick reference
- [ ] Review new utilities module
- [ ] Run test suite (should be 100% pass)
- [ ] Try new user search endpoint
- [ ] Monitor metrics in production
- [ ] Check logs for any errors
- [ ] Collect user feedback
- [ ] Plan Phase 3

---

**Phase 2 Quick Reference v1.0**  
**Last Updated**: Post-deployment  
**Status**: ✅ Ready for production use

