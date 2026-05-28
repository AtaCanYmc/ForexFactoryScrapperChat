"""Pydantic schemas for LLM-based economic event analysis.

Uses Structured Output pattern for reliable JSON parsing from LLMs.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


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
