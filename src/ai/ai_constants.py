from typing import List

LANG_TR = "tr"
LANG_EN = "en"

SITE_MAP = {
    "forex": "src.scrapper.forexFactoryScrapper",
    "cryptocraft": "src.scrapper.cryptoCraftScrapper",
    "metalsmine": "src.scrapper.metalsMineScrapper",
    "energyexch": "src.scrapper.energyExchExchScrapper",
}

FAILED_ANALYZE_CONVERSATION_RESPONSE_EN = {
    "reply": "I'm sorry, I didn't understand your request. Please try again.",
    "analysis": None,
}

NO_EVENTS_FOUND_RESPONSE_EN = {
    "reply": "Sorry, no events found for the requested dates/source.",
    "analysis": None,
}

SERVER_CONFIG_ERROR_EN = {"error": "Server configuration error"}

MAX_DATE_RANGE_DAYS: int = 7
"""Maximum allowed span between start_date and end_date (inclusive)."""

SUPPORTED_SOURCES: List[str] = ["forex", "cryptocraft", "metals", "energy"]
"""Valid values for the ``sources`` parameter."""

SUPPORTED_LANGUAGES: List[str] = [LANG_EN, LANG_TR]
"""Valid values for the ``language`` parameter."""
