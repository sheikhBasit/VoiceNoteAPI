"""
JSON Logger for VoiceNoteAPI

Structured logging with JSON format for better debugging and monitoring.
"""

from datetime import UTC, datetime
import json
import logging
import os
import sys

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "filename": record.filename,
            "funcName": record.funcName,
            "lineno": record.lineno,
            "pathname": record.pathname,
        }

        # Merge in structured fields if present
        extra_fields = getattr(record, "structured_data", None)
        if extra_fields:
            log_record.update(extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_record)


class JsonLogger:
    """
    Structured JSON logger for VoiceNoteAPI.
    
    Usage:
        from app.utils.json_logger import JLogger
        
        JLogger.info("Processing audio file", file_id="123", duration=30.5)
        JLogger.error("Failed to process", error="Invalid format", file_id="456")
    """
    
    def __init__(self, name="app"):
        self._logger = logging.getLogger(name)

        # Avoid duplicate handlers if re-imported
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(JsonFormatter())
            self._logger.addHandler(handler)

        self._logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    def _log(self, level, message, **fields):
        """Internal logging method with structured fields."""
        self._logger.log(
            level,
            message,
            extra={"structured_data": fields},
            stacklevel=3,
        )

    def info(self, message, **fields):
        """Log info level message with optional structured fields."""
        self._log(logging.INFO, message, **fields)

    def debug(self, message, **fields):
        """Log debug level message with optional structured fields."""
        self._log(logging.DEBUG, message, **fields)

    def warning(self, message, **fields):
        """Log warning level message with optional structured fields."""
        self._log(logging.WARNING, message, **fields)

    def error(self, message, **fields):
        """Log error level message with optional structured fields."""
        self._log(logging.ERROR, message, **fields)
    
    def critical(self, message, **fields):
        """Log critical level message with optional structured fields."""
        self._log(logging.CRITICAL, message, **fields)
    
    def exception(self, message, **fields):
        """Log exception with traceback."""
        self._logger.exception(
            message,
            extra={"structured_data": fields},
            stacklevel=2,
        )


# Global logger instance
JLogger = JsonLogger("VoiceNote")
