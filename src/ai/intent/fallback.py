import re
from datetime import date, timedelta, datetime
from typing import Optional, List
from src.ai.ai_constants import LANG_EN
from src.ai.schemas import IntentParsingResult, FetchEconomicDataParams


class SimpleIntentParser:
    """Lightweight, rule-based intent parser for offline / fallback scenarios.

    Does **not** require an LLM.  Uses keyword matching and regex patterns to
    classify intent and extract approximate parameters.
    """

    _DATA_KEYWORDS = {
        "forex",
        "döviz",
        "piyasa",
        "piyasalar",
        "ekonomik",
        "veri",
        "takvim",
        "calendar",
        "data",
        "event",
        "events",
        "crypto",
        "kripto",
        "metal",
        "metals",
        "altın",
        "energy",
        "enerji",
        "petrol",
        "ne oldu",
        "what happened",
        "analiz",
        "analyze",
    }

    _CHAT_KEYWORDS = {
        "selam",
        "merhaba",
        "nasılsın",
        "hello",
        "hi",
        "hey",
        "who are you",
        "sen kimsin",
        "teşekkür",
        "thanks",
        "thank you",
    }

    _SOURCE_MAP = {
        "forex": "forex",
        "döviz": "forex",
        "crypto": "crypto",
        "kripto": "crypto",
        "metal": "metal",
        "metals": "metal",
        "altın": "metal",
        "energy": "energy",
        "enerji": "energy",
        "petrol": "energy",
    }

    _DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

    def parse(
            self,
            user_query: str,
            today: Optional[date] = None,
            language: str = LANG_EN,
    ) -> IntentParsingResult:
        """Parse intent using keyword heuristics."""
        today = today or date.today()
        query_lower = user_query.lower()

        # Check chat first (greetings are usually short)
        if any(kw in query_lower for kw in self._CHAT_KEYWORDS):
            return IntentParsingResult(
                intent_type="chat",
                fetch_params=None,
                chat_response="Hello, How can I assist you today?",
                confidence=0.80,
                reasoning="Greeting / chat keyword detected",
            )

        # Check for data keywords
        if any(kw in query_lower for kw in self._DATA_KEYWORDS):
            sources = self._extract_sources(query_lower)
            start_date, end_date = self._extract_dates(query_lower, today)

            params = FetchEconomicDataParams(
                sources=sources or ["forex"],
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )

            return IntentParsingResult(
                intent_type="fetch_data",
                fetch_params=params,
                chat_response=None,
                confidence=0.70,
                reasoning="Data-related keyword matched (rule-based fallback)",
            )

        # Default: treat as chat
        return IntentParsingResult(
            intent_type="chat",
            fetch_params=None,
            chat_response="Sorry, I couldn't detect a specific intent. How can I assist you today?",
            confidence=0.50,
            reasoning="No strong signal detected; defaulting to chat",
        )

    def _extract_sources(self, query_lower: str) -> List[str]:
        found: List[str] = []
        for keyword, source in self._SOURCE_MAP.items():
            if keyword in query_lower and source not in found:
                found.append(source)
        return found

    def _extract_dates(self, query_lower: str, today: date) -> tuple[date, date]:
        """Best-effort date extraction from query text."""
        # Try explicit YYYY-MM-DD patterns
        matches = self._DATE_RE.findall(query_lower)
        if len(matches) >= 2:
            try:
                d1 = datetime.strptime(matches[0], "%Y-%m-%d").date()
                d2 = datetime.strptime(matches[1], "%Y-%m-%d").date()
                return min(d1, d2), max(d1, d2)
            except ValueError:
                pass

        # Keyword-based relative dates
        if "bugün" in query_lower or "today" in query_lower:
            return today, today
        if "dün" in query_lower or "yesterday" in query_lower:
            return today - timedelta(days=1), today - timedelta(days=1)
        if "geçen hafta" in query_lower or "last week" in query_lower:
            monday_offset = today.weekday()
            last_monday = today - timedelta(days=monday_offset + 7)
            last_sunday = today - timedelta(days=monday_offset + 1)
            return last_monday, last_sunday

        # Default: today
        return today, today
