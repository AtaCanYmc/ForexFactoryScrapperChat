import logging
from datetime import datetime
from typing import Optional
from src.ai.exceptions import IntentParserException
from src.ai.intent.tool_defs import get_fetch_economic_data_tool_definition
from src.ai.providers.base import LLMProvider, IntentParserProvider
from src.ai.schemas import EconomicAnalysisResult, IntentParsingResult
from src.ai.ai_utils import render_analysis_system_prompt, render_analysis_prompt, parse_structured_output, \
    process_fetch_function_calling_response, build_intent_system_prompt, build_intent_user_prompt

logger = logging.getLogger(__name__)


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
    ) -> IntentParsingResult:
        system_prompt = build_intent_system_prompt(current_date)
        user_prompt = build_intent_user_prompt(user_query)
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
            return process_fetch_function_calling_response(response)
        except IntentParserException:
            raise
        except Exception as exc:
            logger.error("OpenAI intent parsing failed: %s", exc)
            raise IntentParserException(f"Intent parsing failed: {exc}") from exc
