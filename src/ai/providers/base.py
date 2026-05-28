from abc import ABC, abstractmethod
from typing import Optional
from src.ai.schemas import EconomicAnalysisResult


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
