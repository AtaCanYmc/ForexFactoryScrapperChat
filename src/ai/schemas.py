"""Pydantic schemas for LLM-based economic event analysis.

Uses Structured Output pattern for reliable JSON parsing from LLMs.
"""
from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from src.ai.ai_constants import LANG_EN, SUPPORTED_SOURCES, MAX_DATE_RANGE_DAYS
from src.ai.exceptions import InvalidDateRangeException, DateRangeExceededException


# ============================================================================
# Analysis
# ============================================================================


class EconomicEvent(BaseModel):
    """Single economic event from scraper.

    Maps directly to scraper output:
    {
        "ID": "event_id",
        "Time": "2026-05-21 14:30:00",
        "Currency": "USD",
        "Event": "Non-Farm Payrolls",
        "Forecast": "150k",
        "Actual": "145k",
        "Previous": "140k",
        "Impact": "high"
    }
    """

    event_id: Optional[str] = Field(None, alias="ID")
    time: str = Field(
        ..., alias="Time", description="Event time in format YYYY-MM-DD HH:MM:SS"
    )
    currency: str = Field(
        ..., alias="Currency", description="Currency code (e.g., USD, EUR)"
    )
    event_name: str = Field(..., alias="Event", description="Event name")
    forecast: str = Field(..., alias="Forecast", description="Forecasted value")
    actual: str = Field(..., alias="Actual", description="Actual value (if released)")
    previous: str = Field(..., alias="Previous", description="Previous period value")
    impact: str = Field(
        ..., alias="Impact", description="Impact level: low, medium, high, or n/a"
    )

    model_config = ConfigDict(populate_by_name=True)  # Allow both field name and alias


class ImpactRating(BaseModel):
    """Impact rating with reasoning."""

    level: str = Field(
        ...,
        description="Impact level: low, medium, high",
        pattern="^(low|medium|high)$",
    )
    reasoning: str = Field(
        ..., description="Brief explanation of why this impact level"
    )


class EventAnalysis(BaseModel):
    """Analysis result for a single economic event."""

    event_name: str = Field(..., description="Name of the economic event")
    currency: str = Field(..., description="Currency code")
    time: str = Field(..., description="Event time")

    # Analysis results
    expectation_vs_previous: str = Field(
        ...,
        description="Analysis of forecast vs previous value (e.g., positive/negative/neutral with % change)",
    )
    actual_vs_expectation: Optional[str] = Field(
        None,
        description="Analysis comparing actual to forecast (if actual is available). Null if not yet released.",
    )
    market_implication: str = Field(
        ...,
        description="Short summary of potential market implications for the currency",
    )
    sentiment: str = Field(
        ...,
        description="Sentiment: bullish, neutral, or bearish for the currency",
        pattern="^(bullish|neutral|bearish)$",
    )
    confidence: str = Field(
        ...,
        description="Analysis confidence: low, medium, high",
        pattern="^(low|medium|high)$",
    )


class EconomicAnalysisResult(BaseModel):
    """Structured output from LLM-based economic event analysis."""

    summary: str = Field(
        ...,
        description="High-level summary for investors (3-5 sentences)",
    )
    analyses: List[EventAnalysis] = Field(
        default_factory=list,
        description="Detailed analysis for each event",
    )
    overall_sentiment: str = Field(
        default="neutral",
        description="Overall market sentiment for the analyzed period: bullish, neutral, bearish",
        pattern="^(bullish|neutral|bearish)$",
    )
    key_events: List[str] = Field(
        default_factory=list,
        description="Top 3-5 most impactful events for trading",
    )
    risk_level: str = Field(
        default="low",
        description="Overall volatility risk for the period: low, medium, high",
        pattern="^(low|medium|high)$",
    )


class AnalysisRequest(BaseModel):
    """Request for economic event analysis.

    Can accept events as either list of dicts (raw scraper output)
    or as EconomicEvent objects.
    """

    events: List[dict] = Field(
        ...,
        description="List of economic events from scraper",
    )
    language: str = Field(
        default="en",
        description="Language for response: en (English), tr (Turkish), etc.",
    )
    focus: Optional[str] = Field(
        None,
        description="Optional focus area: trading, investment, macro, etc.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "events": [
                    {
                        "ID": "123",
                        "Time": "2026-05-21 14:30:00",
                        "Currency": "USD",
                        "Event": "Non-Farm Payrolls",
                        "Forecast": "150k",
                        "Actual": "145k",
                        "Previous": "140k",
                        "Impact": "high",
                    }
                ],
                "language": "en",
                "focus": "trading",
            }
        }
    )


# ============================================================================
# Intent
# ============================================================================

class FetchEconomicDataParams(BaseModel):
    """Parameters extracted by the LLM for the ``fetch_economic_data`` tool."""
    sources: List[str] = Field(...,
                               description=f"Data sources to fetch from. Valid values: {', '.join(SUPPORTED_SOURCES)}")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    language: str = Field(default=LANG_EN, description="Detected user language")

    def validate_sources(self) -> None:
        invalid = set(self.sources) - set(SUPPORTED_SOURCES)
        if invalid:
            raise ValueError(f"Invalid sources: {invalid}. Supported: {SUPPORTED_SOURCES}")

    def validate_dates(self) -> None:
        try:
            start = datetime.strptime(self.start_date, "%Y-%m-%d")
            end = datetime.strptime(self.end_date, "%Y-%m-%d")
        except ValueError as exc:
            raise InvalidDateRangeException(f"Invalid date format (expected YYYY-MM-DD): {exc}") from exc

        if start > end:
            raise InvalidDateRangeException(f"start_date ({self.start_date}) must be ≤ end_date ({self.end_date})")

        span = (end - start).days
        if span > MAX_DATE_RANGE_DAYS:
            raise DateRangeExceededException(f"Date range ({span} days) exceeds maximum ({MAX_DATE_RANGE_DAYS} days).")


class IntentParsingResult(BaseModel):
    """Structured result of intent parsing."""
    intent_type: str = Field(..., description="'fetch_data' for data queries, 'chat' for general conversation")
    intent: Optional[str] = Field(None, description="Alias kept for backward-compat")
    fetch_params: Optional[FetchEconomicDataParams] = Field(None, description="Extracted params")
    chat_response: Optional[str] = Field(None, description="Direct chat response")
    confidence: float = Field(..., description="Confidence score 0.0-1.0")
    reasoning: str = Field(..., description="Brief explanation of classification decision")
    language: str = Field(default="en", description="Detected user language")
    sources: Optional[List[str]] = Field(
        default_factory=list,
        description="List of economic event types",
        examples=["forex", "metal", "crypto", "energy"]
    )
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.intent:
            self.intent = self.intent_type
        if self.fetch_params:
            self.sources = self.fetch_params.sources
            self.start_date = self.fetch_params.start_date
            self.end_date = self.fetch_params.end_date


ParsedIntent = IntentParsingResult
