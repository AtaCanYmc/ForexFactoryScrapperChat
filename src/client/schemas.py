"""Defines Pydantic models for parsing and validating responses from the Scrapper API.

Uses Structured Output pattern for reliable JSON parsing from LLMs.
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class ScrapperEventRecord(BaseModel):
    """Represents a single economic event record returned from the Scrapper API."""
    id: Optional[str] = Field(None, alias="ID")
    time: str = Field(..., alias="Time")
    currency: str = Field(..., alias="Currency")
    event: str = Field(..., alias="Event")
    forecast: str = Field(..., alias="Forecast")
    actual: str = Field(..., alias="Actual")
    previous: str = Field(..., alias="Previous")
    impact: Optional[str] = Field(None, alias="Impact")
    date: str = Field(..., alias="_date")
    source: str = Field(..., alias="_source")

    class Config:
        populate_by_name = True


class PaginatedBundleResponse(BaseModel):
    """Represents the complete envelope structure of the bundle endpoint."""
    total: int
    offset: int
    limit: Optional[int] = None
    start_date: str
    end_date: str
    sources: List[str]
    source_breakdown: Dict[str, int]
    results: List[ScrapperEventRecord]
