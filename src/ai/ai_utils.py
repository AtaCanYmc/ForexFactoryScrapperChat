import os
from datetime import timedelta, datetime
from logging import Logger
from jinja2 import Environment, FileSystemLoader
from src.ai.ai_constants import MAX_DATE_RANGE_DAYS
from src.ai.schemas import EconomicAnalysisResult
import inspect
import json
from datetime import date
from typing import Optional
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


def normalize_sources(sources: list) -> list:
    """Normalize source names to match our internal identifiers."""
    if not sources:
        return ["forex"]

    normalized = []
    for src in sources:
        src_lower = src.lower()
        if src_lower in ("crypto", "kripto"):
            normalized.append("cryptocraft")
        elif src_lower in ("metals", "metal", "altın"):
            normalized.append("metalsmine")
        elif src_lower in ("energy", "enerji"):
            normalized.append("energyexch")
        else:
            normalized.append(src_lower)
    return normalized


def fetch_events(site_map, sources, resolve_helpers, start_date, end_date, logger):
    """Fetch events from specified sources and date range."""
    all_events = []

    for source in sources:
        site_module = site_map.get(source)
        if not site_module:
            logger.warning(f"Unknown source: {source}")
            continue

        try:
            get_records, get_url = resolve_helpers(site_module)
            cur = start_date
            while cur <= end_date:
                url = get_url(cur.day, cur.month, cur.year, "day")
                recs = get_records(url)
                if isinstance(recs, list):
                    all_events.extend(recs)
                elif (
                    isinstance(recs, dict)
                    and "results" in recs
                    and isinstance(recs["results"], list)
                ):
                    all_events.extend(recs["results"])
                cur = cur + timedelta(days=1)
        except Exception as e:
            logger.exception(f"Failed to fetch events from {source}: {e}")
            continue

    return all_events


def render_analysis_prompt(
    *,
    events_data: list,
    language: str = "en",
    focus: Optional[str] = None,
    example_count: int = 0,
    response_style: Optional[str] = None,
    template_name: str = "analysis_prompt.jinja2",
) -> str:
    """Render the analysis prompt using the Jinja2 template.

    This central function allows all providers to render the same prompt with
    extra parameters (example_count, response_style) while keeping a single
    templated source of truth.
    """
    lang_instruction = "English" if language == "en" else language.capitalize()
    events_json = json.dumps(events_data, indent=2)

    templates_dir = os.path.join(os.path.dirname(__file__), "prompts")
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
    language: str = "en",
    template_name: str = "analysis_system_prompt.jinja2",
) -> str:
    """Render the system prompt using the Jinja2 template for analysis.

    This central function allows all providers to render the system prompt with
    templated source of truth.
    """
    lang_instruction = "English" if language == "en" else language.capitalize()

    templates_dir = os.path.join(os.path.dirname(__file__), "prompts")
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
