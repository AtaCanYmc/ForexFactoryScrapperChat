from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from src.ai.schemas import EconomicAnalysisResult, IntentParsingResult


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def analyze_events(
            self,
            events_data: list,
            language: str,
            focus: Optional[str] = None,
            example_count: int = 0,
            response_style: Optional[str] = None,
    ) -> EconomicAnalysisResult:
        """Analyze economic events and return structured result."""
        pass


class IntentParserProvider(ABC):
    """Contract every LLM provider must implement."""

    @abstractmethod
    def parse_intent(
            self,
            user_query: str,
            current_date: datetime
    ) -> IntentParsingResult:
        """Parse user intent from free-form query and return structured result."""
