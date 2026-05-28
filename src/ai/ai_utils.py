import os
from datetime import timedelta, datetime
from logging import Logger
from jinja2 import Environment, FileSystemLoader
from src.ai.ai_constants import MAX_DATE_RANGE_DAYS, SUPPORTED_LANGUAGES
from src.ai.exceptions import IntentParserException
from src.ai.schemas import EconomicAnalysisResult, IntentParsingResult, FetchEconomicDataParams
import inspect
import json
from datetime import date
from typing import Optional, Any
from pydantic import ValidationError


def validate_date_range(
        start_str: Optional[str],
        end_str: Optional[str],
        max_days: int = MAX_DATE_RANGE_DAYS,
) -> tuple[date, date, Optional[str]]:
    """Validate and clamp a pair of date strings.

    Returns:
        ``(start, end, warning)`` – *warning* is ``None`` when the range is
        within limits, otherwise a human-readable message explaining the clip.

    Raises:
        ValueError: On invalid format or ``start > end``.
    """
    if not start_str or not end_str:
        today_dt = date.today()
        return today_dt, today_dt, None

    try:
        start = (
            start_str
            if isinstance(start_str, date)
            else datetime.strptime(start_str, "%Y-%m-%d").date()
        )
        end = (
            end_str
            if isinstance(end_str, date)
            else datetime.strptime(end_str, "%Y-%m-%d").date()
        )
    except ValueError as exc:
        raise ValueError(
            f"Invalid date format. Dates must be in ISO format YYYY-MM-DD. "
            f"Received: start_date='{start_str}', end_date='{end_str}'"
        ) from exc

    if start > end:
        raise ValueError(
            f"Invalid date range: start_date ({start}) cannot be after end_date ({end})."
        )

    span = (end - start).days
    warning: Optional[str] = None

    if span > max_days:
        end = start + timedelta(days=max_days)
        warning = (
            f"Date range too large: {span} days. Clipped to {max_days} days from start_date, "
            f"resulting in end_date={end}."
        )

    return start, end, warning


def render_analysis_user_prompt(
        *,
        events_data: list,
        language: str,
        focus: Optional[str] = None,
        example_count: int = 0,
        response_style: Optional[str] = None,
        template_name: str = "analysis_user_prompt.jinja2",
) -> str:
    """Render the analysis prompt using the Jinja2 template.

    This central function allows all providers to render the same prompt with
    extra parameters (example_count, response_style) while keeping a single
    templated source of truth.
    """
    lang_instruction = language.capitalize()
    events_json = json.dumps(events_data, indent=2)

    templates_dir = os.path.join(os.path.dirname(__file__), "prompts/analysis")
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)
    template = env.get_template(template_name)

    rendered = template.render(
        events_json=events_json,
        focus=focus,
        lang_instruction=lang_instruction,
        example_count=example_count,
        response_style=response_style,
    )

    return inspect.cleandoc(rendered)


def render_analysis_system_prompt(
        *,
        language: str,
        template_name: str = "analysis_system_prompt.jinja2",
) -> str:
    """Render the system prompt using the Jinja2 template for analysis.

    This central function allows all providers to render the system prompt with
    templated source of truth.
    """
    lang_instruction = language.capitalize()

    templates_dir = os.path.join(os.path.dirname(__file__), "prompts/analysis")
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)
    template = env.get_template(template_name)

    rendered = template.render(language=lang_instruction)
    return inspect.cleandoc(rendered)


def parse_structured_output(result_text: str, logger: Logger) -> EconomicAnalysisResult:
    """Parse and validate LLM output as Pydantic model.

    This ensures the output matches our schema exactly.
    Raises ValidationError if parsing fails.
    """
    try:
        # Extract JSON from potential Markdown code blocks
        if "```json" in result_text:
            start = result_text.find("```json") + 7
            end = result_text.find("```", start)
            result_text = result_text[start:end].strip()
        elif "```" in result_text:
            start = result_text.find("```") + 3
            end = result_text.find("```", start)
            result_text = result_text[start:end].strip()

        # Parse JSON
        result_dict = json.loads(result_text)

        # Validate against Pydantic schema
        return EconomicAnalysisResult(**result_dict)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM output as JSON: {e}")
        logger.error(f"Raw output: {result_text[:500]}")
        raise ValueError(f"LLM output is not valid JSON: {e}")
    except ValidationError as e:
        logger.error(f"LLM output failed schema validation: {e}")
        raise ValueError(f"LLM output schema invalid: {e}")


def build_intent_system_prompt(current_date: datetime) -> str:
    date_str = current_date.strftime("%Y-%m-%d (%A)")
    yesterday = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")

    monday_offset = current_date.weekday()
    this_monday = (current_date - timedelta(days=monday_offset)).strftime("%Y-%m-%d")
    last_monday = (current_date - timedelta(days=monday_offset + 7)).strftime("%Y-%m-%d")
    last_sunday = (current_date - timedelta(days=monday_offset + 1)).strftime("%Y-%m-%d")

    templates_dir = os.path.join(os.path.dirname(__file__), "prompts/intent")
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)
    template = env.get_template("intent_system_prompt.jinja2")

    return template.render(
        date_str=date_str, yesterday=yesterday, tomorrow=tomorrow,
        this_monday=this_monday, last_monday=last_monday, last_sunday=last_sunday,
        supported_languages=str(SUPPORTED_LANGUAGES),
    )


def build_intent_user_prompt(user_query: str) -> str:
    return (
        f"User Query: {user_query.strip()}\n\n"
        "Analyze the query above, determine the intent, detect the query language, "
        "and invoke the fetch_economic_data tool if necessary."
    )


def process_fetch_function_calling_response(response: Any) -> IntentParsingResult:
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
                    intent="fetch_data",
                    intent_type="fetch_data",
                    fetch_params=fetch_params,
                    chat_response=None,
                    confidence=0.95,
                    reasoning="LLM invoked fetch_economic_data function call",
                    language=fetch_params.language
                )

        # No tool call → general chat
        return IntentParsingResult(
            intent="chat",
            intent_type="chat",
            fetch_params=None,
            chat_response=message.content or "",
            confidence=0.90,
            reasoning="No data-fetch intent detected; responding as chat",
            language='n/a',
        )
    except (json.JSONDecodeError, ValidationError, AttributeError) as exc:
        raise IntentParserException(f"Response processing failed: {exc}") from exc
