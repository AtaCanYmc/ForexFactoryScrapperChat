import json
from unittest.mock import MagicMock, patch
import pytest
from pydantic import ValidationError

from src.ai.schemas import (
    EconomicEvent,
    EconomicAnalysisResult,
    EventAnalysis,
    IntentParsingResult,
    FetchEconomicDataParams
)
from src.ai.ai_utils import parse_structured_output

def test_economic_event_parsing():
    """Verify EconomicEvent alias parsing works correctly."""
    raw_data = {
        "ID": "event_123",
        "Time": "2026-05-21 14:30:00",
        "Currency": "USD",
        "Event": "Non-Farm Payrolls",
        "Forecast": "150k",
        "Actual": "145k",
        "Previous": "140k",
        "Impact": "high"
    }
    
    event = EconomicEvent(**raw_data)
    assert event.event_id == "event_123"
    assert event.time == "2026-05-21 14:30:00"
    assert event.currency == "USD"
    assert event.event_name == "Non-Farm Payrolls"
    assert event.forecast == "150k"
    assert event.actual == "145k"
    assert event.previous == "140k"
    assert event.impact == "high"

def test_economic_analysis_result_validation():
    """Test validation of structured EconomicAnalysisResult from LLM."""
    raw_analysis = {
        "summary": "Market is showing bullish trend due to NFP beating forecast.",
        "analyses": [
            {
                "event_name": "Non-Farm Payrolls",
                "currency": "USD",
                "time": "2026-05-21 14:30:00",
                "expectation_vs_previous": "Forecast is higher",
                "actual_vs_expectation": "Actual beat expectation",
                "market_implication": "USD strength",
                "sentiment": "bullish",
                "confidence": "high"
            }
        ],
        "overall_sentiment": "bullish",
        "key_events": ["Non-Farm Payrolls"],
        "risk_level": "medium"
    }
    
    result = EconomicAnalysisResult(**raw_analysis)
    assert result.summary == "Market is showing bullish trend due to NFP beating forecast."
    assert len(result.analyses) == 1
    assert result.analyses[0].event_name == "Non-Farm Payrolls"
    assert result.overall_sentiment == "bullish"
    assert result.risk_level == "medium"

def test_parse_structured_output_markdown_stripping():
    """Verify that JSON markdown fences are stripped correctly before parsing."""
    logger_mock = MagicMock()
    raw_md_json = """
```json
{
    "summary": "Test summary",
    "analyses": [],
    "overall_sentiment": "neutral",
    "key_events": [],
    "risk_level": "low"
}
```
"""
    result = parse_structured_output(raw_md_json, logger_mock)
    assert result.summary == "Test summary"
    assert result.overall_sentiment == "neutral"
    assert result.risk_level == "low"

def test_intent_parsing_result_chat():
    """Test IntentParsingResult default post-init behavior for general chat."""
    chat_intent = {
        "intent_type": "chat",
        "confidence": 0.9,
        "reasoning": "User greeted the bot",
        "language": "tr",
        "chat_response": "Merhaba! Size nasil yardimci olabilirim?"
    }
    
    parsed = IntentParsingResult(**chat_intent)
    assert parsed.intent == "chat"
    assert parsed.intent_type == "chat"
    assert parsed.sources == []
    assert parsed.start_date is None

def test_intent_parsing_result_fetch_data():
    """Test IntentParsingResult with fetch_params."""
    fetch_intent = {
        "intent_type": "fetch_data",
        "confidence": 0.95,
        "reasoning": "User asked about economic calendar",
        "language": "en",
        "fetch_params": {
            "sources": ["forex"],
            "start_date": "2026-05-24",
            "end_date": "2026-05-26",
            "language": "en"
        }
    }
    
    parsed = IntentParsingResult(**fetch_intent)
    assert parsed.intent == "fetch_data"
    assert parsed.sources == ["forex"]
    assert parsed.start_date == "2026-05-24"
    assert parsed.end_date == "2026-05-26"
