import json
import logging
from datetime import datetime
from typing import Optional
from pydantic import ValidationError
from src.ai.exceptions import IntentParserException
from src.ai.providers.base import LLMProvider, IntentParserProvider
from src.ai.schemas import EconomicAnalysisResult, IntentParsingResult
from src.ai.ai_utils import render_analysis_user_prompt, parse_structured_output, build_intent_system_prompt, \
    build_intent_user_prompt

logger = logging.getLogger(__name__)


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
            history: Optional[list] = None,
    ) -> EconomicAnalysisResult:
        """Analyze events using local Ollama model."""
        try:
            # Render prompt from shared template; allow optional style/examples
            prompt = render_analysis_user_prompt(
                events_data=events_data,
                language=language,
                focus=focus,
                example_count=example_count,
                response_style=response_style,
            )

            history_str = ""
            if history:
                history_str = "Chat History:\n"
                for turn in history:
                    role = "Assistant" if turn.get("role") == "bot" else "User"
                    history_str += f"{role}: {turn.get('text', '')}\n"
                history_str += "\n"

            full_prompt = history_str + prompt

            response = self.requests.post(
                self.endpoint,
                json={"model": self.model, "prompt": full_prompt, "stream": False},
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
        return render_analysis_user_prompt(
            events_data=events_data,
            language=language,
            focus=focus,
        )


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
            history: Optional[list] = None,
    ) -> IntentParsingResult:
        system_prompt = build_intent_system_prompt(current_date)
        user_prompt = build_intent_user_prompt(user_query)

        history_str = ""
        if history:
            history_str = "Chat History:\n"
            for turn in history:
                role = "Assistant" if turn.get("role") == "bot" else "User"
                history_str += f"{role}: {turn.get('text', '')}\n"
            history_str += "\n"

        full_prompt = (
            f"{system_prompt}\n\n"
            f"{history_str}"
            f"{user_prompt}\n\n"
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
        # Strip Markdown code fences if present
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
