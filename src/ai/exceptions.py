class IntentParserException(Exception):
    """Base exception for intent parsing errors."""


class DateRangeExceededException(IntentParserException):
    """Raised when date range exceeds maximum allowed days."""


class InvalidDateRangeException(IntentParserException):
    """Raised when date range is invalid (end before start, bad format, etc.)."""


class NoIntentDetectedException(IntentParserException):
    """Raised when no data-retrieval intent is detected (general chat)."""
