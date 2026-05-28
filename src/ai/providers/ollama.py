import logging
from typing import Optional
from src.ai.providers.base import LLMProvider
from src.ai.schemas import EconomicAnalysisResult
from src.ai.ai_utils import render_analysis_system_prompt, render_analysis_prompt, parse_structured_output

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
