import logging
import os
from datetime import date, datetime
from typing import Optional, Dict, Any
from src.ai.exceptions import IntentParserException, DateRangeExceededException, InvalidDateRangeException
from src.ai.providers import (
    OllamaIntentParserProvider,
    GroqIntentParserProvider,
    OpenAIIntentParserProvider,
    IntentParserProvider
)
from src.ai.schemas import IntentParsingResult

logger = logging.getLogger(__name__)


class IntentParser:
    """Facade that selects the LLM provider and delegates intent parsing."""

    def __init__(self, provider: Optional[str] = None, current_date: Optional[datetime] = None,
                 **provider_kwargs: Any) -> None:
        self.provider = self._init_provider(provider, provider_kwargs)
        self.current_date = current_date or datetime(2026, 5, 24)

    @staticmethod
    def _init_provider(provider: Optional[str], kwargs: Dict[str, Any]) -> IntentParserProvider:
        name = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower()

        if name == "ollama":
            base_url = kwargs.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model = kwargs.get("model") or os.getenv("OLLAMA_MODEL", "qwen:7b")
            return OllamaIntentParserProvider(base_url=base_url, model=model)
        if name == "groq":
            api_key = kwargs.get("api_key") or os.getenv("GROQ_API_KEY")
            if not api_key: raise ValueError("GROQ_API_KEY required")
            model = kwargs.get("model") or os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
            return GroqIntentParserProvider(api_key=api_key, model=model)
        if name == "openai":
            api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key: raise ValueError("OPENAI_API_KEY required")
            model = kwargs.get("model") or os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
            return OpenAIIntentParserProvider(api_key=api_key, model=model)

        raise ValueError(f"Unknown LLM provider: {name}.")

    def parse(self, user_query: str, today: Optional[date] = None,
              history: Optional[list] = None) -> IntentParsingResult:
        if not user_query or not user_query.strip():
            raise ValueError("User query cannot be empty")

        eval_date = datetime.combine(today, datetime.min.time()) if today else self.current_date

        try:
            return self.provider.parse_intent(user_query=user_query, current_date=eval_date, history=history)
        except (DateRangeExceededException, InvalidDateRangeException):
            raise
        except IntentParserException:
            raise
        except Exception as exc:
            logger.error("Intent parsing failed: %s", exc)
            raise IntentParserException(f"Failed to parse intent: {exc}") from exc
