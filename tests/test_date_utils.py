from datetime import date, timedelta
import pytest
from src.ai.ai_utils import validate_date_range

def test_validate_date_range_valid():
    """Test valid date range within limits."""
    start_str = "2026-05-20"
    end_str = "2026-05-25"
    start, end, warning = validate_date_range(start_str, end_str)
    
    assert start == date(2026, 5, 20)
    assert end == date(2026, 5, 25)
    assert warning is None

def test_validate_date_range_clamp():
    """Test date range clamping when span is greater than max_days."""
    start_str = "2026-05-10"
    end_str = "2026-05-25" # 15 days span
    start, end, warning = validate_date_range(start_str, end_str, max_days=7)
    
    assert start == date(2026, 5, 10)
    assert end == date(2026, 5, 17) # Clipped to exactly 7 days
    assert warning is not None
    assert "Clipped to 7 days" in warning

def test_validate_date_range_none():
    """Test handling of None arguments (should default to today)."""
    start, end, warning = validate_date_range(None, None)
    
    assert start == date.today()
    assert end == date.today()
    assert warning is None

def test_validate_date_range_invalid_order():
    """Test ValueError raised when start is after end."""
    start_str = "2026-05-25"
    end_str = "2026-05-20"
    
    with pytest.raises(ValueError) as exc:
        validate_date_range(start_str, end_str)
    
    assert "cannot be after end_date" in str(exc.value)

def test_validate_date_range_invalid_format():
    """Test ValueError raised on malformed date string."""
    with pytest.raises(ValueError) as exc:
        validate_date_range("2026-05/20", "2026-05-25")
    
    assert "Invalid date format" in str(exc.value)

def test_validate_date_range_date_objects():
    """Test when input is already date objects."""
    d1 = date(2026, 5, 24)
    d2 = date(2026, 5, 28)
    start, end, warning = validate_date_range(d1, d2)
    
    assert start == d1
    assert end == d2
    assert warning is None
