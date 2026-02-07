"""
Phase 2 - AI Service Utilities Unit Tests

Pure unit tests that don't require the full AI service dependencies.
Tests focus on validation, retry logic, rate limiting, and request tracking.
"""

import time

import pytest

from app.utils.ai_service_utils import (
    AIServiceError,
    RateLimiter,
    RequestTracker,
    RetryExhaustedError,
    retry_with_backoff,
    validate_ai_response,
    validate_json_response,
    validate_transcript,
)


class TestTranscriptValidation:
    """Test transcript validation functionality."""

    def test_valid_transcript(self):
        """✅ Valid transcript passes validation."""
        result = validate_transcript("  This is a valid transcript  ")
        assert result == "This is a valid transcript"

    def test_empty_transcript(self):
        """✅ Empty transcript raises error."""
        with pytest.raises(AIServiceError, match="cannot be empty"):
            validate_transcript("")

    def test_whitespace_only_transcript(self):
        """✅ Whitespace-only transcript raises error."""
        with pytest.raises(AIServiceError, match="cannot be empty"):
            validate_transcript("   ")

    def test_very_long_transcript(self):
        """✅ Transcript exceeding max length raises error."""
        long_text = "a" * 100001
        with pytest.raises(AIServiceError, match="too long"):
            validate_transcript(long_text)

    def test_max_length_transcript(self):
        """✅ Transcript at max length passes."""
        max_text = "a" * 100000
        result = validate_transcript(max_text)
        assert len(result) == 100000


class TestJSONValidation:
    """Test JSON response validation."""

    def test_valid_json_dict(self):
        """✅ Valid JSON dictionary passes."""
        json_str = '{"tasks": ["task1", "task2"], "summary": "test"}'
        result = validate_json_response(json_str)
        assert result == {"tasks": ["task1", "task2"], "summary": "test"}

    def test_empty_json_string(self):
        """✅ Empty JSON string raises error."""
        with pytest.raises(AIServiceError, match="Empty JSON"):
            validate_json_response("")

    def test_whitespace_only_json(self):
        """✅ Whitespace-only JSON string raises error."""
        with pytest.raises(AIServiceError, match="Empty JSON"):
            validate_json_response("   ")

    def test_invalid_json(self):
        """✅ Invalid JSON raises error."""
        with pytest.raises(AIServiceError, match="Invalid JSON"):
            validate_json_response("{invalid json}")

    def test_json_array_not_object(self):
        """✅ JSON array (not object) raises error."""
        with pytest.raises(AIServiceError, match="must be an object"):
            validate_json_response('["task1", "task2"]')

    def test_json_string_not_object(self):
        """✅ JSON string (not object) raises error."""
        with pytest.raises(AIServiceError, match="must be an object"):
            validate_json_response('"just a string"')

    def test_complex_json_object(self):
        """✅ Complex nested JSON object passes."""
        json_str = '{"tasks": [{"id": 1, "title": "Task 1"}], "metadata": {"total": 1}}'
        result = validate_json_response(json_str)
        assert result["tasks"][0]["title"] == "Task 1"


class TestResponseValidation:
    """Test AI response validation."""

    def test_valid_response(self):
        """✅ Valid response passes validation."""
        response = {"tasks": ["task1"], "summary": "test"}
        result = validate_ai_response(response, ["tasks", "summary"])
        assert result == response

    def test_missing_required_field(self):
        """✅ Missing required field raises error."""
        response = {"tasks": ["task1"]}
        with pytest.raises(AIServiceError, match="Missing required field"):
            validate_ai_response(response, ["tasks", "summary"])

    def test_none_required_field(self):
        """✅ None value in required field raises error."""
        response = {"tasks": ["task1"], "summary": None}
        with pytest.raises(AIServiceError, match="cannot be None"):
            validate_ai_response(response, ["tasks", "summary"])

    def test_extra_fields_allowed(self):
        """✅ Extra fields beyond required fields are allowed."""
        response = {"tasks": ["task1"], "summary": "test", "extra": "allowed"}
        result = validate_ai_response(response, ["tasks", "summary"])
        assert "extra" in result

    def test_single_required_field(self):
        """✅ Single required field validation."""
        response = {"data": "value"}
        result = validate_ai_response(response, ["data"])
        assert result["data"] == "value"


class TestRetryDecorator:
    """Test retry decorator with exponential backoff."""

    def test_success_on_first_attempt(self):
        """✅ Successful call on first attempt."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, initial_backoff=0.01)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count == 1

    def test_success_after_failures(self):
        """✅ Successful call after initial failures."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, initial_backoff=0.01)
        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} fails")
            return "success"

        result = sometimes_fails()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """✅ Retry exhaustion after max attempts."""
        call_count = 0

        @retry_with_backoff(max_attempts=2, initial_backoff=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryExhaustedError) as exc_info:
            always_fails()

        assert call_count == 2
        assert "All 2 attempts exhausted" in str(exc_info.value)

    def test_exponential_backoff_timing(self):
        """✅ Exponential backoff increases wait time."""
        start_time = time.time()
        call_count = 0

        @retry_with_backoff(
            max_attempts=3, initial_backoff=0.05, backoff_multiplier=2.0
        )
        def retry_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "done"

        result = retry_function()
        elapsed = time.time() - start_time

        assert result == "done"
        assert call_count == 3
        # Waits: 0.05 + 0.1 = 0.15 seconds minimum
        assert elapsed >= 0.15

    def test_specific_exception_handling(self):
        """✅ Only specified exceptions trigger retry."""

        @retry_with_backoff(
            max_attempts=3,
            initial_backoff=0.01,
            exceptions=(ValueError,),  # Only retry on ValueError
        )
        def selective_retry():
            raise TypeError("This won't be retried")

        with pytest.raises(TypeError):
            selective_retry()


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_allow_requests_under_limit(self):
        """✅ Requests allowed when under limit."""
        limiter = RateLimiter(max_requests=5, time_window=1.0)

        for i in range(5):
            assert limiter.allow_request() is True

    def test_reject_requests_over_limit(self):
        """✅ Requests rejected when over limit."""
        limiter = RateLimiter(max_requests=2, time_window=1.0)

        assert limiter.allow_request() is True
        assert limiter.allow_request() is True
        assert limiter.allow_request() is False

    def test_rate_limit_resets_after_window(self):
        """✅ Rate limiter resets after time window."""
        limiter = RateLimiter(max_requests=1, time_window=0.1)

        assert limiter.allow_request() is True
        assert limiter.allow_request() is False

        time.sleep(0.15)

        assert limiter.allow_request() is True

    def test_get_wait_time_when_allowed(self):
        """✅ Wait time is 0 when request allowed."""
        limiter = RateLimiter(max_requests=2, time_window=1.0)
        assert limiter.allow_request() is True
        assert limiter.get_wait_time() == 0.0

    def test_get_wait_time_when_limited(self):
        """✅ Wait time is positive when rate limited."""
        limiter = RateLimiter(max_requests=1, time_window=0.2)

        assert limiter.allow_request() is True
        assert limiter.allow_request() is False

        wait_time = limiter.get_wait_time()
        assert 0.1 < wait_time <= 0.2

    def test_multiple_rate_limiters_independent(self):
        """✅ Multiple limiters work independently."""
        limiter1 = RateLimiter(max_requests=2, time_window=1.0)
        limiter2 = RateLimiter(max_requests=3, time_window=1.0)

        # Fill limiter1
        limiter1.allow_request()
        limiter1.allow_request()

        # Limiter2 still has requests
        assert limiter2.allow_request() is True
        assert limiter2.allow_request() is True


class TestRequestTracker:
    """Test request tracking functionality."""

    def test_track_successful_request(self):
        """✅ Track successful request."""
        tracker = RequestTracker()

        tracker.start_request("req_001", "groq", model="whisper")
        time.sleep(0.02)
        tracker.end_request("req_001", success=True)

        metrics = tracker.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["total_errors"] == 0
        assert metrics["error_rate"] == 0.0
        assert metrics["avg_latency"] >= 0.02

    def test_track_failed_request(self):
        """✅ Track failed request."""
        tracker = RequestTracker()

        tracker.start_request("req_002", "deepgram")
        time.sleep(0.01)
        tracker.end_request("req_002", success=False, error_msg="Network error")

        metrics = tracker.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["total_errors"] == 1
        assert metrics["error_rate"] == 1.0

    def test_track_multiple_requests(self):
        """✅ Track multiple mixed requests."""
        tracker = RequestTracker()

        # Successful request
        tracker.start_request("req_001", "groq")
        time.sleep(0.01)
        tracker.end_request("req_001", success=True)

        # Failed request
        tracker.start_request("req_002", "deepgram")
        time.sleep(0.02)
        tracker.end_request("req_002", success=False, error_msg="Timeout")

        # Another successful request
        tracker.start_request("req_003", "llm")
        time.sleep(0.01)
        tracker.end_request("req_003", success=True)

        metrics = tracker.get_metrics()
        assert metrics["total_requests"] == 3
        assert metrics["total_errors"] == 1
        assert abs(metrics["error_rate"] - 1 / 3) < 0.01

    def test_error_rate_calculation(self):
        """✅ Error rate calculated correctly."""
        tracker = RequestTracker()

        # Add 4 successful and 1 failed
        for i in range(5):
            tracker.start_request(f"req_{i:03d}", "test")
            time.sleep(0.01)
            success = i != 4  # Last one fails
            tracker.end_request(f"req_{i:03d}", success=success)

        metrics = tracker.get_metrics()
        assert metrics["total_requests"] == 5
        assert metrics["total_errors"] == 1
        assert abs(metrics["error_rate"] - 0.2) < 0.01

    def test_average_latency(self):
        """✅ Average latency calculated correctly."""
        tracker = RequestTracker()

        # Add requests with different latencies
        for i in range(3):
            tracker.start_request(f"req_{i:03d}", "test")
            time.sleep(0.02)  # 20ms each
            tracker.end_request(f"req_{i:03d}", success=True)

        metrics = tracker.get_metrics()
        assert metrics["total_requests"] == 3
        assert metrics["avg_latency"] >= 0.02


class TestValidationChaining:
    """Test validators working together."""

    def test_transcript_then_json(self):
        """✅ Validate transcript then JSON."""
        transcript = validate_transcript("  Valid input  ")
        assert transcript == "Valid input"

        json_data = validate_json_response('{"data": "value"}')
        assert json_data["data"] == "value"

    def test_json_then_response_validation(self):
        """✅ Validate JSON then response structure."""
        json_data = validate_json_response('{"tasks": ["t1"], "summary": "s"}')

        response = validate_ai_response(json_data, ["tasks", "summary"])
        assert response["tasks"][0] == "t1"

    def test_all_validators_together(self):
        """✅ All validators in sequence."""
        # Transcript
        transcript = validate_transcript("  Meeting notes  ")
        assert len(transcript) > 0

        # JSON response
        response_json = '{"tasks": ["note"], "summary": "summary"}'
        parsed = validate_json_response(response_json)

        # Response structure
        final = validate_ai_response(parsed, ["tasks", "summary"])
        assert "tasks" in final


# Integration/End-to-End Tests
class TestIntegration:
    """Integration tests combining multiple components."""

    def test_retry_with_rate_limiting(self):
        """✅ Retry decorator works with rate limiter."""
        limiter = RateLimiter(max_requests=5, time_window=1.0)
        attempts = []

        @retry_with_backoff(max_attempts=3, initial_backoff=0.01)
        def rate_limited_function():
            attempts.append(1)
            if not limiter.allow_request():
                raise RuntimeError("Rate limited")
            return "success"

        result = rate_limited_function()
        assert result == "success"

    def test_request_tracking_with_validation(self):
        """✅ Request tracking works with validation."""
        tracker = RequestTracker()

        # Simulate processing chain
        tracker.start_request("chain_001", "audio_processing")
        try:
            transcript = validate_transcript("  Valid audio  ")
            response = validate_json_response('{"data": "result"}')
            validate_ai_response(response, ["data"])
            tracker.end_request("chain_001", success=True)
        except Exception as e:
            tracker.end_request("chain_001", success=False, error_msg=str(e))

        metrics = tracker.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["total_errors"] == 0

    def test_error_scenario_handling(self):
        """✅ Error scenarios handled correctly."""
        tracker = RequestTracker()

        # Successful request
        tracker.start_request("req_1", "service_a")
        tracker.end_request("req_1", success=True)

        # Failed request
        tracker.start_request("req_2", "service_b")
        tracker.end_request("req_2", success=False, error_msg="Timeout")

        # Failed validation
        with pytest.raises(AIServiceError):
            validate_transcript("")

        metrics = tracker.get_metrics()
        assert metrics["total_errors"] == 1
        assert metrics["error_rate"] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
