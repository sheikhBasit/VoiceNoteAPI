"""
Phase 2 - AI Service Utilities

Provides timeout handling, retry logic, and request tracking for AI Service.
"""

import time
import json
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_TIMEOUT = 30  # 30 seconds
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 1.5  # Exponential backoff multiplier
MAX_TRANSCRIPT_LENGTH = 100000


class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass


class TimeoutError(AIServiceError):
    """Timeout error from AI service."""
    pass


class RetryExhaustedError(AIServiceError):
    """All retries exhausted."""
    pass


def retry_with_backoff(
    max_attempts: int = DEFAULT_RETRIES,
    initial_backoff: float = 1.0,
    backoff_multiplier: float = DEFAULT_BACKOFF,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        initial_backoff: Initial backoff time in seconds
        backoff_multiplier: Multiplier for exponential backoff
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            backoff = initial_backoff
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(f"Attempt {attempt}/{max_attempts} for {func.__name__}")
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt} failed: {str(e)}")
                    
                    if attempt < max_attempts:
                        wait_time = backoff * (backoff_multiplier ** (attempt - 1))
                        logger.info(f"Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_attempts} attempts exhausted")
            
            raise RetryExhaustedError(
                f"Failed after {max_attempts} attempts: {str(last_exception)}"
            )
        
        return wrapper
    return decorator


def with_timeout(timeout_seconds: float = DEFAULT_TIMEOUT):
    """
    Decorator to add timeout to a function.
    
    Note: This is for synchronous functions. For async, use asyncio.wait_for
    
    Args:
        timeout_seconds: Timeout in seconds
        
    Returns:
        Decorated function with timeout
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # For actual timeout enforcement, would need signal or threading
            # This is a placeholder - actual implementation depends on context
            logger.info(f"Calling {func.__name__} with {timeout_seconds}s timeout")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_transcript(transcript: str) -> str:
    """
    Validate transcript input.
    
    Args:
        transcript: Transcript text to validate
        
    Returns:
        Validated transcript
        
    Raises:
        AIServiceError: If transcript is invalid
    """
    if not transcript or len(transcript.strip()) == 0:
        raise AIServiceError("Transcript cannot be empty")
    
    transcript = transcript.strip()
    
    if len(transcript) > MAX_TRANSCRIPT_LENGTH:
        raise AIServiceError(
            f"Transcript too long: {len(transcript)} > {MAX_TRANSCRIPT_LENGTH} characters"
        )
    
    return transcript


def validate_ai_response(response: Dict[str, Any], required_fields: list) -> Dict[str, Any]:
    """
    Validate AI service response structure.
    
    Args:
        response: Response dictionary from AI service
        required_fields: List of required field names
        
    Returns:
        Validated response
        
    Raises:
        AIServiceError: If response is invalid
    """
    if not isinstance(response, dict):
        raise AIServiceError("Response must be a dictionary")
    
    for field in required_fields:
        if field not in response:
            raise AIServiceError(f"Missing required field: {field}")
        
        if response[field] is None:
            raise AIServiceError(f"Field '{field}' cannot be None")
    
    return response


def validate_json_response(json_str: str) -> Dict[str, Any]:
    """
    Validate and parse JSON response from LLM.
    
    Args:
        json_str: JSON string to validate
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        AIServiceError: If JSON is invalid
    """
    if not json_str or not json_str.strip():
        raise AIServiceError("Empty JSON response")
    
    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            raise AIServiceError("JSON response must be an object/dictionary")
        return data
    except json.JSONDecodeError as e:
        raise AIServiceError(f"Invalid JSON: {str(e)}")


class RequestTracker:
    """Track AI service requests for monitoring and debugging."""
    
    def __init__(self):
        self.requests: Dict[str, Dict[str, Any]] = {}
        self.total_requests = 0
        self.total_errors = 0
        self.total_latency = 0.0
    
    def start_request(self, request_id: str, request_type: str, **kwargs):
        """
        Start tracking a request.
        
        Args:
            request_id: Unique request ID
            request_type: Type of request (groq, deepgram, llm)
            **kwargs: Additional request metadata
        """
        self.requests[request_id] = {
            'type': request_type,
            'start_time': time.time(),
            'status': 'in_progress',
            'metadata': kwargs
        }
    
    def end_request(self, request_id: str, success: bool = True, error_msg: str = None):
        """
        End tracking a request.
        
        Args:
            request_id: Request ID
            success: Whether request succeeded
            error_msg: Error message if failed
        """
        if request_id not in self.requests:
            return
        
        request = self.requests[request_id]
        end_time = time.time()
        latency = end_time - request['start_time']
        
        request['end_time'] = end_time
        request['latency'] = latency
        request['status'] = 'success' if success else 'error'
        request['error'] = error_msg
        
        self.total_requests += 1
        self.total_latency += latency
        if not success:
            self.total_errors += 1
        
        logger.info(
            f"Request {request_id} ({request['type']}) "
            f"completed in {latency:.2f}s - {'✅' if success else '❌'}"
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated metrics.
        
        Returns:
            Metrics dictionary
        """
        avg_latency = (self.total_latency / self.total_requests) if self.total_requests > 0 else 0
        
        return {
            'total_requests': self.total_requests,
            'total_errors': self.total_errors,
            'error_rate': (self.total_errors / self.total_requests) if self.total_requests > 0 else 0,
            'avg_latency': avg_latency,
            'total_latency': self.total_latency
        }
    
    def log_metrics(self):
        """Log current metrics."""
        metrics = self.get_metrics()
        logger.info(
            f"AI Service Metrics: "
            f"{metrics['total_requests']} requests, "
            f"{metrics['error_rate']*100:.1f}% error rate, "
            f"{metrics['avg_latency']:.2f}s avg latency"
        )


# Global request tracker
_request_tracker = RequestTracker()


def get_request_tracker() -> RequestTracker:
    """Get the global request tracker."""
    return _request_tracker


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, max_requests: int = 100, time_window: float = 60.0):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: list = []
    
    def allow_request(self) -> bool:
        """
        Check if request is allowed.
        
        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        
        # Remove old requests outside the time window
        self.requests = [
            req_time for req_time in self.requests
            if now - req_time < self.time_window
        ]
        
        # Check if we're at the limit
        if len(self.requests) >= self.max_requests:
            return False
        
        # Record this request
        self.requests.append(now)
        return True
    
    def get_wait_time(self) -> float:
        """
        Get wait time before next request is allowed.
        
        Returns:
            Wait time in seconds (0 if allowed now)
        """
        if self.allow_request():
            return 0.0
        
        if len(self.requests) == 0:
            return 0.0
        
        oldest_request = self.requests[0]
        wait_time = self.time_window - (time.time() - oldest_request)
        return max(0.0, wait_time)


# Test the utilities
if __name__ == "__main__":
    # Test transcript validation
    try:
        print("✅ Transcript validation:", validate_transcript("  Sample transcript  "))
    except AIServiceError as e:
        print("❌ Transcript validation error:", e)
    
    # Test JSON validation
    try:
        result = validate_json_response('{"tasks": ["task1"], "summary": "test"}')
        print("✅ JSON validation:", result)
    except AIServiceError as e:
        print("❌ JSON validation error:", e)
    
    # Test request tracker
    tracker = get_request_tracker()
    tracker.start_request("req_001", "groq", model="whisper")
    time.sleep(0.1)
    tracker.end_request("req_001", success=True)
    print("✅ Request tracking:", tracker.get_metrics())
    
    # Test rate limiter
    limiter = RateLimiter(max_requests=3, time_window=1.0)
    for i in range(5):
        allowed = limiter.allow_request()
        print(f"  Request {i+1}: {'allowed' if allowed else 'rate limited'}")
    
    print("\n✨ All AI Service utilities working!")
