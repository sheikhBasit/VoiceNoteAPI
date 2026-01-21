#!/usr/bin/env python
"""
Phase 2 - AI Service Utilities Standalone Test

Tests utilities without pytest framework to avoid fixture issues.
Run directly: python standalone_test_ai_utilities.py
"""

import time
import sys

# Add parent directory to path
sys.path.insert(0, '/home/aoi/Desktop/mnt/muaaz/VoiceNote')

from app.utils.ai_service_utils import (
    retry_with_backoff,
    validate_transcript,
    validate_json_response,
    validate_ai_response,
    RequestTracker,
    RateLimiter,
    AIServiceError,
    RetryExhaustedError
)

# Test results
passed = 0
failed = 0
total = 0

def test(name, func):
    """Run a test function and track results."""
    global passed, failed, total
    total += 1
    try:
        func()
        print(f"✅ PASS: {name}")
        passed += 1
    except Exception as e:
        print(f"❌ FAIL: {name}")
        print(f"   Error: {e}")
        failed += 1


# ============================================================================
# TRANSCRIPT VALIDATION TESTS
# ============================================================================

def test_valid_transcript():
    result = validate_transcript("  Valid transcript  ")
    assert result == "Valid transcript"

def test_empty_transcript():
    try:
        validate_transcript("")
        raise AssertionError("Should have raised AIServiceError")
    except AIServiceError:
        pass

def test_whitespace_only():
    try:
        validate_transcript("   ")
        raise AssertionError("Should have raised AIServiceError")
    except AIServiceError:
        pass

def test_too_long_transcript():
    try:
        validate_transcript("a" * 100001)
        raise AssertionError("Should have raised AIServiceError")
    except AIServiceError:
        pass


# ============================================================================
# JSON VALIDATION TESTS
# ============================================================================

def test_valid_json():
    result = validate_json_response('{"tasks": ["task1"], "summary": "test"}')
    assert result == {"tasks": ["task1"], "summary": "test"}

def test_empty_json():
    try:
        validate_json_response("")
        raise AssertionError("Should have raised AIServiceError")
    except AIServiceError:
        pass

def test_invalid_json_syntax():
    try:
        validate_json_response("{invalid}")
        raise AssertionError("Should have raised AIServiceError")
    except AIServiceError:
        pass

def test_json_array_error():
    try:
        validate_json_response('["task1", "task2"]')
        raise AssertionError("Should have raised AIServiceError")
    except AIServiceError:
        pass


# ============================================================================
# RESPONSE VALIDATION TESTS
# ============================================================================

def test_valid_response():
    response = {"tasks": ["task1"], "summary": "test"}
    result = validate_ai_response(response, ["tasks", "summary"])
    assert result == response

def test_missing_required_field():
    try:
        validate_ai_response({"tasks": ["task1"]}, ["tasks", "summary"])
        raise AssertionError("Should have raised AIServiceError")
    except AIServiceError:
        pass

def test_none_required_field():
    try:
        validate_ai_response({"tasks": None, "summary": "test"}, ["tasks", "summary"])
        raise AssertionError("Should have raised AIServiceError")
    except AIServiceError:
        pass


# ============================================================================
# RETRY DECORATOR TESTS
# ============================================================================

def test_retry_first_attempt():
    call_count = 0
    
    @retry_with_backoff(max_attempts=3, initial_backoff=0.01)
    def success_func():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = success_func()
    assert result == "success"
    assert call_count == 1

def test_retry_after_failure():
    call_count = 0
    
    @retry_with_backoff(max_attempts=3, initial_backoff=0.01)
    def retry_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("Try again")
        return "success"
    
    result = retry_func()
    assert result == "success"
    assert call_count == 2

def test_retry_exhausted():
    call_count = 0
    
    @retry_with_backoff(max_attempts=2, initial_backoff=0.01)
    def always_fails():
        nonlocal call_count
        call_count += 1
        raise ValueError("Always fails")
    
    try:
        always_fails()
        raise AssertionError("Should have raised RetryExhaustedError")
    except RetryExhaustedError:
        assert call_count == 2


# ============================================================================
# RATE LIMITER TESTS
# ============================================================================

def test_rate_limiter_allow():
    limiter = RateLimiter(max_requests=5, time_window=1.0)
    for i in range(5):
        assert limiter.allow_request() is True

def test_rate_limiter_block():
    limiter = RateLimiter(max_requests=2, time_window=1.0)
    assert limiter.allow_request() is True
    assert limiter.allow_request() is True
    assert limiter.allow_request() is False

def test_rate_limiter_reset():
    limiter = RateLimiter(max_requests=1, time_window=0.1)
    assert limiter.allow_request() is True
    assert limiter.allow_request() is False
    time.sleep(0.15)
    assert limiter.allow_request() is True


# ============================================================================
# REQUEST TRACKER TESTS
# ============================================================================

def test_tracker_success():
    tracker = RequestTracker()
    tracker.start_request("req_001", "groq")
    time.sleep(0.01)
    tracker.end_request("req_001", success=True)
    
    metrics = tracker.get_metrics()
    assert metrics['total_requests'] == 1
    assert metrics['total_errors'] == 0
    assert metrics['error_rate'] == 0.0

def test_tracker_error():
    tracker = RequestTracker()
    tracker.start_request("req_001", "groq")
    time.sleep(0.01)
    tracker.end_request("req_001", success=False, error_msg="Timeout")
    
    metrics = tracker.get_metrics()
    assert metrics['total_requests'] == 1
    assert metrics['total_errors'] == 1
    assert metrics['error_rate'] == 1.0

def test_tracker_multiple():
    tracker = RequestTracker()
    
    # 2 successful
    for i in range(2):
        tracker.start_request(f"req_{i}", "groq")
        time.sleep(0.01)
        tracker.end_request(f"req_{i}", success=True)
    
    # 1 failed
    tracker.start_request("req_2", "groq")
    time.sleep(0.01)
    tracker.end_request("req_2", success=False, error_msg="Error")
    
    metrics = tracker.get_metrics()
    assert metrics['total_requests'] == 3
    assert metrics['total_errors'] == 1


# ============================================================================
# RUN ALL TESTS
# ============================================================================

def main():
    print("\n" + "="*70)
    print("Phase 2 - AI Service Utilities Standalone Tests")
    print("="*70 + "\n")
    
    # Transcript validation
    print("📝 Transcript Validation Tests:")
    test("Valid transcript", test_valid_transcript)
    test("Empty transcript error", test_empty_transcript)
    test("Whitespace only error", test_whitespace_only)
    test("Too long transcript error", test_too_long_transcript)
    
    # JSON validation
    print("\n📋 JSON Validation Tests:")
    test("Valid JSON", test_valid_json)
    test("Empty JSON error", test_empty_json)
    test("Invalid JSON syntax error", test_invalid_json_syntax)
    test("JSON array error", test_json_array_error)
    
    # Response validation
    print("\n✓ Response Validation Tests:")
    test("Valid response", test_valid_response)
    test("Missing required field error", test_missing_required_field)
    test("None required field error", test_none_required_field)
    
    # Retry decorator
    print("\n🔄 Retry Decorator Tests:")
    test("Retry - first attempt success", test_retry_first_attempt)
    test("Retry - success after failure", test_retry_after_failure)
    test("Retry - exhausted", test_retry_exhausted)
    
    # Rate limiter
    print("\n⏱️  Rate Limiter Tests:")
    test("Rate limiter - allow under limit", test_rate_limiter_allow)
    test("Rate limiter - block over limit", test_rate_limiter_block)
    test("Rate limiter - reset after window", test_rate_limiter_reset)
    
    # Request tracker
    print("\n📊 Request Tracker Tests:")
    test("Tracker - success", test_tracker_success)
    test("Tracker - error", test_tracker_error)
    test("Tracker - multiple requests", test_tracker_multiple)
    
    # Summary
    print("\n" + "="*70)
    print(f"📈 Test Results: {passed}/{total} passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"❌ {failed} test(s) failed")
    print("="*70 + "\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
