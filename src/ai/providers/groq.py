import logging
from datetime import datetime
from typing import Optional
from src.ai.exceptions import IntentParserException
from src.ai.intent.tool_defs import get_fetch_economic_data_tool_definition
from src.ai.providers.base import LLMProvider, IntentParserProvider
from src.ai.schemas import EconomicAnalysisResult, IntentParsingResult
from src.ai.ai_utils import render_analysis_system_prompt, render_analysis_user_prompt, parse_structured_output, \
    process_fetch_function_calling_response, build_intent_system_prompt, build_intent_user_prompt

logger = logging.getLogger(__name__)


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
            history: Optional[list] = None,
    ) -> EconomicAnalysisResult:
        """Analyze events using Groq API with structured output."""
        try:
            system_prompt = render_analysis_system_prompt(language=language)
            # Use shared renderer; pass example_count/response_style through
            user_prompt = render_analysis_user_prompt(
                events_data=events_data,
                language=language,
                focus=focus,
                example_count=example_count,
                response_style=response_style,
            )

            messages_payload = [{"role": "system", "content": system_prompt}]
            if history:
                for turn in history:
                    role = "assistant" if turn.get("role") == "bot" else "user"
                    messages_payload.append({"role": role, "content": turn.get("text", "")})
            messages_payload.append({"role": "user", "content": user_prompt})

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
            history: Optional[list] = None,
    ) -> IntentParsingResult:
        system_prompt = build_intent_system_prompt(current_date)
        user_prompt = build_intent_user_prompt(user_query)
        tools = [get_fetch_economic_data_tool_definition()]

        try:
            messages_payload = [{"role": "system", "content": system_prompt}]
            if history:
                for turn in history:
                    role = "assistant" if turn.get("role") == "bot" else "user"
                    messages_payload.append({"role": role, "content": turn.get("text", "")})
            messages_payload.append({"role": "user", "content": user_prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_payload,  # type: ignore
                tools=tools,  # type: ignore
                tool_choice="auto",
                temperature=0.3,
                timeout=30,
            )
            return process_fetch_function_calling_response(response)
        except IntentParserException:
            raise
        except Exception as exc:
            logger.error("Groq intent parsing failed: %s", exc)
            raise IntentParserException(f"Intent parsing failed: {exc}") from exc
