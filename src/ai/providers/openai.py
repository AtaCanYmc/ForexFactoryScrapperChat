import logging
from typing import Optional
from src.ai.providers.base import LLMProvider
from src.ai.schemas import EconomicAnalysisResult
from src.ai.ai_utils import render_analysis_system_prompt, render_analysis_prompt, parse_structured_output

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
