from typing import Dict, Any
from src.ai.ai_constants import SUPPORTED_SOURCES, SUPPORTED_LANGUAGES


def get_fetch_economic_data_tool_definition() -> Dict[str, Any]:
    """Return the tool/function schema consumed by OpenAI / Groq ``tools`` param."""
    return {
        "type": "function",
        "function": {
            "name": "fetch_economic_data",
            "description": "Fetch economic calendar data from specified sources within a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sources": {
                        "type": "array",
                        "items": {"type": "string", "enum": SUPPORTED_SOURCES},
                        "description": (
                            f"Data sources to query. "
                            f"Valid values: {', '.join(SUPPORTED_SOURCES)}"
                        ),
                    },
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    "language": {
                        "type": "string",
                        "enum": SUPPORTED_LANGUAGES,
                        "description": (
                            f"The language of the user's query. "
                            f"Supported values: {', '.join(SUPPORTED_LANGUAGES)}."
                        ),
                    },
                },
                "required": ["sources", "start_date", "end_date", "language"],
            },
        },
    }
