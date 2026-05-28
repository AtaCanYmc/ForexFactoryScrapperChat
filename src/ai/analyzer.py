"""LLM-based economic event analyzer with provider flexibility.

Supports:
- Local: Ollama (any model like Qwen, Llama, etc.)
- Cloud: Groq, OpenAI
"""

import logging
import os
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from .ai_utils import (
    render_analysis_prompt,
    parse_structured_output,
    render_analysis_system_prompt,
)
from .schemas import (
    AnalysisRequest,
    EconomicAnalysisResult,
)

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def analyze_events(
            self,
            events_data: list,
            language: str,  # like 'en'
            focus: Optional[str] = None,
            example_count: int = 0,
            response_style: Optional[str] = None,
    ) -> EconomicAnalysisResult:
        """Analyze economic events and return structured result."""
        pass


class OllamaProvider(LLMProvider):
    """Local LLM provider using Ollama (self-hosted).

    Supports any model available on Ollama (Qwen, Llama, etc.)
    Requires: OLLAMA_BASE_URL, OLLAMA_MODEL env vars
    Example: http://localhost:11434
    """

    def __init__(self, base_url: str, model: str):
        """Initialize Ollama provider.

        Args:
            base_url: Ollama server URL (e.g., http://localhost:11434)
            model: Model name (e.g., qwen:7b, llama2, etc.)
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.endpoint = f"{self.base_url}/api/generate"

        # Import here to avoid hard dependency
        try:
            import requests

            self.requests = requests
        except ImportError:
            raise ImportError("requests library required for OllamaProvider")

    def analyze_events(
            self,
            events_data: list,
            language: str,
            focus: Optional[str] = None,
            example_count: int = 0,
            response_style: Optional[str] = None,
    ) -> EconomicAnalysisResult:
        """Analyze events using local Ollama model."""
        try:
            # Render prompt from shared template; allow optional style/examples
            prompt = render_analysis_prompt(
                events_data=events_data,
                language=language,
                focus=focus,
                example_count=example_count,
                response_style=response_style,
            )

            response = self.requests.post(
                self.endpoint,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=120,
            )
            response.raise_for_status()

            result_text = response.json().get("response", "")
            return parse_structured_output(result_text, logger)

        except Exception as e:
            logger.error(f"Ollama analysis failed: {e}")
            raise

    @staticmethod
    def _build_analysis_prompt(
            events_data: list,
            language: str,
            focus: Optional[str],
    ) -> str:
        """Build analysis prompt for the LLM."""
        # Delegate to shared renderer with defaults for example_count and response_style
        return render_analysis_prompt(
            events_data=events_data,
            language=language,
            focus=focus,
        )


class GroqProvider(LLMProvider):
    """Cloud LLM provider using Groq API (fast inference).

    Requires: GROQ_API_KEY env var
    """

    def __init__(self, api_key: str, model: str = "mixtral-8x7b-32768"):
        """Initialize Groq provider.

        Args:
            api_key: Groq API key
            model: Model name (default: mixtral-8x7b-32768)
        """
        self.api_key = api_key
        self.model = model

        try:
            from groq import Groq

            self.client = Groq(api_key=api_key)
        except ImportError:
            raise ImportError(
                "groq library required for GroqProvider. Install with: pip install groq"
            )

    def analyze_events(
            self,
            events_data: list,
            language: str,
            focus: Optional[str] = None,
            example_count: int = 0,
            response_style: Optional[str] = None,
    ) -> EconomicAnalysisResult:
        """Analyze events using Groq API with structured output."""
        try:
            system_prompt = render_analysis_system_prompt(language=language)
            # Use shared renderer; pass example_count/response_style through
            user_prompt = render_analysis_prompt(
                events_data=events_data,
                language=language,
                focus=focus,
                example_count=example_count,
                response_style=response_style,
            )

            messages_payload = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},  # type: ignore
                messages=messages_payload,  # type: ignore
                temperature=0.2,
                top_p=0.9,
                timeout=30,
            )

            result_text = response.choices[0].message.content
            return parse_structured_output(result_text, logger)

        except Exception as e:
            logger.error(f"Groq analysis failed: {e}")
            raise


class OpenAIProvider(LLMProvider):
    """Cloud LLM provider using OpenAI API.

    Requires: OPENAI_API_KEY env var
    """

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4-turbo-preview)
        """
        self.api_key = api_key
        self.model = model

        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError(
                "openai library required for OpenAIProvider. Install with: pip install openai"
            )

    def analyze_events(
            self,
            events_data: list,
            language: str,
            focus: Optional[str] = None,
            example_count: int = 0,
            response_style: Optional[str] = None,
    ) -> EconomicAnalysisResult:
        """Analyze events using OpenAI API with structured output."""
        try:
            system_prompt = render_analysis_system_prompt(language=language)
            user_prompt = render_analysis_prompt(
                events_data=events_data,
                language=language,
                focus=focus,
                example_count=example_count,
                response_style=response_style,
            )

            response = self.client.chat.completions.create(
                response_format={"type": "json_object"},  # type: ignore
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                timeout=30,
            )

            result_text = response.choices[0].message.content
            return parse_structured_output(result_text, logger)

        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            raise


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
