import logging
from typing import Optional
from src.ai.providers.base import LLMProvider
from src.ai.schemas import EconomicAnalysisResult
from src.ai.ai_utils import render_analysis_system_prompt, render_analysis_prompt, parse_structured_output

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
