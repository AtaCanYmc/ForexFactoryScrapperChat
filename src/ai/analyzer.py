"""LLM-based economic event analyzer with provider flexibility.

Supports:
- Local: Ollama (any model like Qwen, Llama, etc.)
- Cloud: Groq, OpenAI
"""

import logging
import os
from .providers import LLMProvider, OllamaProvider, GroqProvider, OpenAIProvider
from typing import Optional, Dict, Any
from .schemas import (
    AnalysisRequest,
    EconomicAnalysisResult,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Economic Analyzer (main class that selects provider and performs analysis)
# ============================================================================


class EconomicAnalyzer:
    """Main analyzer class that orchestrates LLM provider selection and analysis.

    Supports provider selection via environment variables or constructor args:
    - Local Ollama: LLM_PROVIDER=ollama, OLLAMA_BASE_URL, OLLAMA_MODEL
    - Groq: LLM_PROVIDER=groq, GROQ_API_KEY, GROQ_MODEL (optional)
    - OpenAI: LLM_PROVIDER=openai, OPENAI_API_KEY, OPENAI_MODEL (optional)
    """

    def __init__(
            self,
            provider: Optional[str] = None,
            **provider_kwargs,
    ):
        """Initialize analyzer with LLM provider.

        Args:
            provider: Provider name (ollama, groq, openai). Auto-detected from env if None.
            **provider_kwargs: Additional kwargs for provider (api_key, model, base_url, etc.)
        """
        self.provider = self._init_provider(provider, provider_kwargs)

    @staticmethod
    def _init_provider(provider: Optional[str], kwargs: Dict[str, Any]) -> LLMProvider:
        """Initialize LLM provider from environment or explicit config."""
        provider_name = provider or os.getenv("LLM_PROVIDER", "ollama").lower()

        if provider_name == "ollama":
            base_url = kwargs.get("base_url") or os.getenv(
                "OLLAMA_BASE_URL", "http://localhost:11434"
            )
            model = kwargs.get("model") or os.getenv("OLLAMA_MODEL", "qwen:7b")
            logger.info(f"Initializing Ollama provider: {model} at {base_url}")
            return OllamaProvider(base_url=base_url, model=model)

        elif provider_name == "groq":
            api_key = kwargs.get("api_key") or os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY required for Groq provider")
            model = kwargs.get("model") or os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
            logger.info(f"Initializing Groq provider: {model}")
            return GroqProvider(api_key=api_key, model=model)

        elif provider_name == "openai":
            api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY required for OpenAI provider")
            model = kwargs.get("model") or os.getenv(
                "OPENAI_MODEL", "gpt-4-turbo-preview"
            )
            logger.info(f"Initializing OpenAI provider: {model}")
            return OpenAIProvider(api_key=api_key, model=model)

        else:
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                "Supported: ollama, groq, openai"
            )

    def analyze(
            self,
            request: AnalysisRequest,
            example_count: int = 0,
            response_style: Optional[str] = None,
    ) -> EconomicAnalysisResult:
        """Analyze economic events from request.

        Args:
            request: AnalysisRequest with events and parameters
            example_count: Number of examples to analyze
            response_style: Response style to use

        Returns:
            EconomicAnalysisResult with structured output

        Raises:
            ValueError: If events list is empty or LLM fails
        """
        if not request.events or len(request.events) == 0:
            logger.info(
                "No events found in the request. Skipping LLM call and returning empty result."
            )
            return EconomicAnalysisResult(
                summary="There are no economic calendar events or crypto data recorded for this specific period.",
                analyses=[],
                overall_sentiment="neutral",
                key_events=[],
                risk_level="low",
            )

        try:
            result = self.provider.analyze_events(
                events_data=request.events,
                language=request.language,
                focus=request.focus,
                example_count=example_count,
                response_style=response_style,
            )
            return result
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
