"""Intent Parsing for economic calendar queries using LLM Function-Calling / Tool-Use.

Architecture
============
1. **Models** – Pydantic schemas for parameters and results.
2. **Tool Definition** – OpenAI-compatible tool/function spec for ``fetch_economic_data``.
3. **Provider ABC** – ``IntentParserProvider`` with ``parse_intent`` contract.
4. **Concrete Providers** – Ollama (structured JSON), Groq & OpenAI (function-calling).
5. **Orchestrator** – ``IntentParser`` selects provider, validates output, enforces limits.
6. **Helpers** – ``validate_date_range`` reused by Flask routes.
"""

from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field, ValidationError

from src.ai.ai_constants import (
    SUPPORTED_SOURCES,
    MAX_DATE_RANGE_DAYS,
    LANG_EN,
    SUPPORTED_LANGUAGES,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class IntentParserException(Exception):
    """Base exception for intent parsing errors."""


class DateRangeExceededException(IntentParserException):
    """Raised when date range exceeds maximum allowed days."""


class InvalidDateRangeException(IntentParserException):
    """Raised when date range is invalid (end before start, bad format, etc.)."""


class NoIntentDetectedException(IntentParserException):
    """Raised when no data-retrieval intent is detected (general chat)."""


# ============================================================================
# Pydantic Models
# ============================================================================


class FetchEconomicDataParams(BaseModel):
    """Parameters extracted by the LLM for the ``fetch_economic_data`` tool."""

    sources: List[str] = Field(
        ...,
        description=(
            "Data sources to fetch from. "
            f"Valid values: {', '.join(SUPPORTED_SOURCES)}"
        ),
    )
    start_date: str = Field(
        ...,
        description="Start date in YYYY-MM-DD format",
    )
    end_date: str = Field(
        ...,
        description="End date in YYYY-MM-DD format",
    )
    language: str = Field(default=LANG_EN, description="Detected user language")

    # -- validation helpers --------------------------------------------------

    def validate_sources(self) -> None:
        """Raise ``ValueError`` if any source is not in ``SUPPORTED_SOURCES``."""
        invalid = set(self.sources) - set(SUPPORTED_SOURCES)
        if invalid:
            raise ValueError(
                f"Invalid sources: {invalid}. Supported: {SUPPORTED_SOURCES}"
            )

    def validate_dates(self) -> None:
        """Raise if format/order/range is invalid."""
        try:
            start = datetime.strptime(self.start_date, "%Y-%m-%d")
            end = datetime.strptime(self.end_date, "%Y-%m-%d")
        except ValueError as exc:
            raise InvalidDateRangeException(
                f"Invalid date format (expected YYYY-MM-DD): {exc}"
            ) from exc

        if start > end:
            raise InvalidDateRangeException(
                f"start_date ({self.start_date}) must be ≤ end_date ({self.end_date})"
            )

        span = (end - start).days
        if span > MAX_DATE_RANGE_DAYS:
            raise DateRangeExceededException(
                f"Date range ({span} days) exceeds maximum "
                f"({MAX_DATE_RANGE_DAYS} days). Please narrow your query."
            )


class IntentParsingResult(BaseModel):
    """Structured result of intent parsing.

    ``intent_type`` is the canonical discriminator:
      * ``"fetch_data"`` – user wants economic calendar data.
      * ``"chat"``       – general conversation / greeting.
    """

    intent_type: str = Field(
        ...,
        description="'fetch_data' for data queries, 'chat' for general conversation",
    )
    intent: Optional[str] = Field(
        None,
        description="Alias kept for backward-compat with router semantics",
    )
    fetch_params: Optional[FetchEconomicDataParams] = Field(
        None,
        description="Extracted params when intent_type is 'fetch_data'",
    )
    chat_response: Optional[str] = Field(
        None,
        description="Direct chat response when intent_type is 'chat'",
    )
    confidence: float = Field(
        ...,
        description="Confidence score 0.0-1.0",
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of classification decision",
    )
    language: str = Field(
        default="en", description="Detected user language: like 'tr' or 'en'"
    )

    # Flat convenience fields (populated from fetch_params)
    sources: Optional[List[str]] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        """Sync flat fields from nested ``fetch_params``."""
        if not self.intent:
            self.intent = self.intent_type
        if self.fetch_params:
            self.sources = self.fetch_params.sources
            self.start_date = self.fetch_params.start_date
            self.end_date = self.fetch_params.end_date


# Backward-compatibility alias used by existing test scripts.
ParsedIntent = IntentParsingResult


# ============================================================================
# Tool / Function Definition (OpenAI-compatible spec)
# ============================================================================


def get_fetch_economic_data_tool_definition() -> Dict[str, Any]:
    """Return the tool/function schema consumed by OpenAI / Groq ``tools`` param."""
    return {
        "type": "function",
        "function": {
            "name": "fetch_economic_data",
            "description": (
                "Fetch economic calendar data from specified sources within a "
                "date range. Call this tool when the user asks about economic "
                "events, forex news, calendar data, metals, energy or crypto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": SUPPORTED_SOURCES,
                        },
                        "description": (
                            f"Data sources to query. "
                            f"Valid values: {', '.join(SUPPORTED_SOURCES)}"
                        ),
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                    },
                    "language": {
                        "type": "string",
                        "enum": SUPPORTED_LANGUAGES,
                        "description": (
                            f"The language of the user's query. "
                            f"Supported values: {', '.join(SUPPORTED_LANGUAGES)}. "
                            f"Defaults to '{LANG_EN}' if context is ambiguous."
                        ),
                    },
                },
                "required": ["sources", "start_date", "end_date", "language"],
            },
        },
    }


# ============================================================================
# System / User Prompt Builders
# ============================================================================


def build_system_prompt(current_date: datetime) -> str:
    """Build the system prompt using the Jinja2 template with dynamically computed dates."""

    date_str = current_date.strftime("%Y-%m-%d (%A)")
    yesterday = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")

    monday_offset = current_date.weekday()
    this_monday = (current_date - timedelta(days=monday_offset)).strftime("%Y-%m-%d")
    last_monday = (current_date - timedelta(days=monday_offset + 7)).strftime(
        "%Y-%m-%d"
    )
    last_sunday = (current_date - timedelta(days=monday_offset + 1)).strftime(
        "%Y-%m-%d"
    )

    templates_dir = os.path.join(os.path.dirname(__file__), "prompts")
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)
    template = env.get_template("intent_system_prompt.jinja2")

    return template.render(
        date_str=date_str,
        yesterday=yesterday,
        tomorrow=tomorrow,
        this_monday=this_monday,
        last_monday=last_monday,
        last_sunday=last_sunday,
        supported_languages=str(SUPPORTED_LANGUAGES),
    )


def build_user_prompt(user_query: str) -> str:
    """Wrap raw user input into the user-role message using clean English boundaries."""
    return (
        f"User Query: {user_query.strip()}\n\n"
        "Analyze the query above, determine the intent, detect the query language, "
        "and invoke the fetch_economic_data tool if necessary."
    )


# ============================================================================
# Provider ABC
# ============================================================================


class IntentParserProvider(ABC):
    """Contract every LLM provider must implement."""

    @abstractmethod
    def parse_intent(
        self,
        user_query: str,
        current_date: datetime,
        language: str = LANG_EN,
    ) -> IntentParsingResult:
        """Parse user intent from free-form query and return structured result."""


# ============================================================================
# Ollama Provider (local, JSON-based structured output)
# ============================================================================


class OllamaIntentParserProvider(IntentParserProvider):
    """Uses local Ollama server with raw JSON structured output."""

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.endpoint = f"{self.base_url}/api/generate"

        try:
            import requests  # noqa: F811 – local import to avoid hard dependency

            self._requests = requests
        except ImportError as exc:
            raise ImportError(
                "requests library required for OllamaIntentParserProvider"
            ) from exc

    def parse_intent(
        self,
        user_query: str,
        current_date: datetime,
        language: str = LANG_EN,
    ) -> IntentParsingResult:
        system_prompt = build_system_prompt(current_date)
        user_prompt = build_user_prompt(user_query)

        full_prompt = (
            f"{system_prompt}\n\n{user_prompt}\n\n"
            "Yanıtını aşağıdaki JSON yapısında ver:\n"
            "{\n"
            '  "intent_type": "fetch_data" veya "chat",\n'
            '  "fetch_params": {"sources": [...], "start_date": "YYYY-MM-DD", '
            '"end_date": "YYYY-MM-DD"} (fetch_data ise, değilse null),\n'
            '  "chat_response": "yanıtın" (chat ise, değilse null),\n'
            '  "confidence": 0.0-1.0,\n'
            '  "reasoning": "kısa açıklama"\n'
            "}\n\n"
            "SADECE JSON nesnesi ile yanıt ver, başka metin ekleme."
        )

        try:
            response = self._requests.post(
                self.endpoint,
                json={"model": self.model, "prompt": full_prompt, "stream": False},
                timeout=60,
            )
            response.raise_for_status()
            result_text = response.json().get("response", "")
            return self._parse_json_output(result_text)
        except IntentParserException:
            raise
        except Exception as exc:
            logger.error("Ollama intent parsing failed: %s", exc)
            raise IntentParserException(f"Intent parsing failed: {exc}") from exc

    @staticmethod
    def _parse_json_output(raw: str) -> IntentParsingResult:
        """Extract and validate JSON from Ollama's free-form text response."""
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if "```json" in cleaned:
            start = cleaned.index("```json") + 7
            end = cleaned.index("```", start)
            cleaned = cleaned[start:end].strip()
        elif "```" in cleaned:
            start = cleaned.index("```") + 3
            end = cleaned.index("```", start)
            cleaned = cleaned[start:end].strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Ollama output as JSON: %s", cleaned[:300])
            raise IntentParserException(f"Invalid JSON response: {exc}") from exc

        try:
            result = IntentParsingResult(**data)
        except ValidationError as exc:
            logger.error("Schema validation failed: %s", exc)
            raise IntentParserException(f"Schema validation failed: {exc}") from exc

        if result.intent_type == "fetch_data" and result.fetch_params:
            result.fetch_params.validate_sources()
            result.fetch_params.validate_dates()

        return result


# ============================================================================
# Groq Provider (cloud, native function-calling)
# ============================================================================


class GroqIntentParserProvider(IntentParserProvider):
    """Uses Groq cloud API with native ``tools`` / function-calling."""

    def __init__(self, api_key: str, model: str = "mixtral-8x7b-32768") -> None:
        self.api_key = api_key
        self.model = model

        try:
            from groq import Groq

            self.client = Groq(api_key=api_key)
        except ImportError as exc:
            raise ImportError(
                "groq library required for GroqIntentParserProvider"
            ) from exc

    def parse_intent(
        self,
        user_query: str,
        current_date: datetime,
        language: str = LANG_EN,
    ) -> IntentParsingResult:
        system_prompt = build_system_prompt(current_date)
        user_prompt = build_user_prompt(user_query)
        tools = [get_fetch_economic_data_tool_definition()]

        try:
            messages_payload = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_payload,  # type: ignore
                tools=tools,  # type: ignore
                tool_choice="auto",
                temperature=0.3,
                timeout=30,
            )
            return _process_function_calling_response(response)
        except IntentParserException:
            raise
        except Exception as exc:
            logger.error("Groq intent parsing failed: %s", exc)
            raise IntentParserException(f"Intent parsing failed: {exc}") from exc


# ============================================================================
# OpenAI Provider (cloud, native function-calling)
# ============================================================================


class OpenAIIntentParserProvider(IntentParserProvider):
    """Uses OpenAI API with native ``tools`` / function-calling."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview") -> None:
        self.api_key = api_key
        self.model = model

        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key)
        except ImportError as exc:
            raise ImportError(
                "openai library required for OpenAIIntentParserProvider"
            ) from exc

    def parse_intent(
        self,
        user_query: str,
        current_date: datetime,
        language: str = LANG_EN,
    ) -> IntentParsingResult:
        system_prompt = build_system_prompt(current_date)
        user_prompt = build_user_prompt(user_query)
        tools = [get_fetch_economic_data_tool_definition()]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=tools,
                tool_choice="auto",
                temperature=0.3,
                timeout=30,
            )
            return _process_function_calling_response(response)
        except IntentParserException:
            raise
        except Exception as exc:
            logger.error("OpenAI intent parsing failed: %s", exc)
            raise IntentParserException(f"Intent parsing failed: {exc}") from exc


# ============================================================================
# Shared Response Processor (Groq & OpenAI share the same response shape)
# ============================================================================


def _process_function_calling_response(response: Any) -> IntentParsingResult:
    """Process an OpenAI-compatible chat completion that may contain tool_calls.

    If the model invoked ``fetch_economic_data``, build a ``fetch_data`` result.
    Otherwise, treat the reply as general chat.
    """
    try:
        message = response.choices[0].message

        if message.tool_calls:
            tool_call = message.tool_calls[0]
            if tool_call.function.name == "fetch_economic_data":
                params_dict = json.loads(tool_call.function.arguments)
                fetch_params = FetchEconomicDataParams(**params_dict)
                fetch_params.validate_sources()
                fetch_params.validate_dates()

                return IntentParsingResult(
                    intent_type="fetch_data",
                    fetch_params=fetch_params,
                    chat_response=None,
                    confidence=0.95,
                    reasoning="LLM invoked fetch_economic_data function call",
                )

        # No tool call → general chat
        return IntentParsingResult(
            intent_type="chat",
            fetch_params=None,
            chat_response=message.content or "",
            confidence=0.90,
            reasoning="No data-fetch intent detected; responding as chat",
        )
    except (json.JSONDecodeError, ValidationError, AttributeError) as exc:
        logger.error("Failed to process function-calling response: %s", exc)
        raise IntentParserException(f"Response processing failed: {exc}") from exc


# ============================================================================
# Simple Rule-Based Fallback Parser
# ============================================================================


class SimpleIntentParser:
    """Lightweight, rule-based intent parser for offline / fallback scenarios.

    Does **not** require an LLM.  Uses keyword matching and regex patterns to
    classify intent and extract approximate parameters.
    """

    _DATA_KEYWORDS = {
        "forex",
        "döviz",
        "piyasa",
        "piyasalar",
        "ekonomik",
        "veri",
        "takvim",
        "calendar",
        "data",
        "event",
        "events",
        "crypto",
        "kripto",
        "metal",
        "metals",
        "altın",
        "energy",
        "enerji",
        "petrol",
        "ne oldu",
        "what happened",
        "analiz",
        "analyze",
    }

    _CHAT_KEYWORDS = {
        "selam",
        "merhaba",
        "nasılsın",
        "hello",
        "hi",
        "hey",
        "who are you",
        "sen kimsin",
        "teşekkür",
        "thanks",
        "thank you",
    }

    _SOURCE_MAP = {
        "forex": "forex",
        "döviz": "forex",
        "crypto": "cryptocraft",
        "kripto": "cryptocraft",
        "metal": "metals",
        "metals": "metals",
        "altın": "metals",
        "energy": "energy",
        "enerji": "energy",
        "petrol": "energy",
    }

    _DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

    def parse(
        self,
        user_query: str,
        today: Optional[date] = None,
        language: str = LANG_EN,
    ) -> IntentParsingResult:
        """Parse intent using keyword heuristics."""
        today = today or date.today()
        query_lower = user_query.lower()

        # Check chat first (greetings are usually short)
        if any(kw in query_lower for kw in self._CHAT_KEYWORDS):
            return IntentParsingResult(
                intent_type="chat",
                fetch_params=None,
                chat_response="Hello, How can I assist you today?",
                confidence=0.80,
                reasoning="Greeting / chat keyword detected",
            )

        # Check for data keywords
        if any(kw in query_lower for kw in self._DATA_KEYWORDS):
            sources = self._extract_sources(query_lower)
            start_date, end_date = self._extract_dates(query_lower, today)

            params = FetchEconomicDataParams(
                sources=sources or ["forex"],
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )

            return IntentParsingResult(
                intent_type="fetch_data",
                fetch_params=params,
                chat_response=None,
                confidence=0.70,
                reasoning="Data-related keyword matched (rule-based fallback)",
            )

        # Default: treat as chat
        return IntentParsingResult(
            intent_type="chat",
            fetch_params=None,
            chat_response="Sorry, I couldn't detect a specific intent. How can I assist you today?",
            confidence=0.50,
            reasoning="No strong signal detected; defaulting to chat",
        )

    def _extract_sources(self, query_lower: str) -> List[str]:
        found: List[str] = []
        for keyword, source in self._SOURCE_MAP.items():
            if keyword in query_lower and source not in found:
                found.append(source)
        return found

    def _extract_dates(self, query_lower: str, today: date) -> tuple[date, date]:
        """Best-effort date extraction from query text."""
        # Try explicit YYYY-MM-DD patterns
        matches = self._DATE_RE.findall(query_lower)
        if len(matches) >= 2:
            try:
                d1 = datetime.strptime(matches[0], "%Y-%m-%d").date()
                d2 = datetime.strptime(matches[1], "%Y-%m-%d").date()
                return min(d1, d2), max(d1, d2)
            except ValueError:
                pass

        # Keyword-based relative dates
        if "bugün" in query_lower or "today" in query_lower:
            return today, today
        if "dün" in query_lower or "yesterday" in query_lower:
            return today - timedelta(days=1), today - timedelta(days=1)
        if "geçen hafta" in query_lower or "last week" in query_lower:
            monday_offset = today.weekday()
            last_monday = today - timedelta(days=monday_offset + 7)
            last_sunday = today - timedelta(days=monday_offset + 1)
            return last_monday, last_sunday

        # Default: today
        return today, today


# ============================================================================
# Main Orchestrator
# ============================================================================


class IntentParser:
    """Facade that selects the LLM provider and delegates intent parsing.

    Provider is chosen from ``LLM_PROVIDER`` env var or constructor arg::

        parser = IntentParser()                          # reads .env
        parser = IntentParser(provider="groq", api_key="…")
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        current_date: Optional[datetime] = None,
        **provider_kwargs: Any,
    ) -> None:
        self.provider = self._init_provider(provider, provider_kwargs)
        self.current_date = current_date or datetime(2026, 5, 24)

    # -- provider factory ----------------------------------------------------

    @staticmethod
    def _init_provider(
        provider: Optional[str],
        kwargs: Dict[str, Any],
    ) -> IntentParserProvider:
        name = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower()

        if name == "ollama":
            base_url = kwargs.get("base_url") or os.getenv(
                "OLLAMA_BASE_URL", "http://localhost:11434"
            )
            model = kwargs.get("model") or os.getenv("OLLAMA_MODEL", "qwen:7b")
            return OllamaIntentParserProvider(base_url=base_url, model=model)

        if name == "groq":
            api_key = kwargs.get("api_key") or os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY required for Groq provider")
            model = kwargs.get("model") or os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
            return GroqIntentParserProvider(api_key=api_key, model=model)

        if name == "openai":
            api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY required for OpenAI provider")
            model = kwargs.get("model") or os.getenv(
                "OPENAI_MODEL", "gpt-4-turbo-preview"
            )
            return OpenAIIntentParserProvider(api_key=api_key, model=model)

        raise ValueError(
            f"Unknown LLM provider: {name}. Supported: ollama, groq, openai"
        )

    # -- public API ----------------------------------------------------------

    def parse(
        self,
        user_query: str,
        today: Optional[date] = None,
        language: str = LANG_EN,
    ) -> IntentParsingResult:
        """Parse *user_query* and return structured intent with parameters.

        Raises:
            ValueError: Empty query.
            DateRangeExceededException: Span > 7 days.
            InvalidDateRangeException: Bad dates.
            IntentParserException: LLM / network failures.
        """
        if not user_query or not user_query.strip():
            raise ValueError("User query cannot be empty")

        eval_date = (
            datetime.combine(today, datetime.min.time()) if today else self.current_date
        )

        try:
            return self.provider.parse_intent(
                user_query=user_query,
                current_date=eval_date,
                language=language,
            )
        except (DateRangeExceededException, InvalidDateRangeException):
            raise
        except IntentParserException:
            raise
        except Exception as exc:
            logger.error("Intent parsing failed: %s", exc)
            raise IntentParserException(f"Failed to parse intent: {exc}") from exc
