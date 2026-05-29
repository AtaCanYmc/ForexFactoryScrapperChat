"""Flask routes for AI-powered economic event analysis."""

import logging
from flask import Blueprint, request, jsonify
from datetime import date

from src.ai.ai_constants import (
    FAILED_ANALYZE_CONVERSATION_RESPONSE_EN,
    NO_EVENTS_FOUND_RESPONSE_EN,
    SERVER_CONFIG_ERROR_EN,
)
from src.ai.ai_utils import validate_date_range
from src.ai.analyzer import EconomicAnalyzer
from src.ai.intent_parser import IntentParser
from src.ai.schemas import AnalysisRequest

logger = logging.getLogger(__name__)

ai_bp = Blueprint("ai", __name__)

# Global instances for lazy-loading
_analyzer = None
_intent_parser = None
_api_client = None


def get_analyzer():
    """Get or initialize the analyzer (lazy loading)."""
    global _analyzer
    if _analyzer is None:
        try:
            _analyzer = EconomicAnalyzer()
            logger.info("Economic analyzer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize analyzer: {e}")
            raise
    return _analyzer


def get_intent_parser():
    """Get or initialize the intent parser (lazy loading)."""
    global _intent_parser
    if _intent_parser is None:
        try:
            _intent_parser = IntentParser()
            logger.info("Intent parser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize intent parser: {e}")
            raise
    return _intent_parser


def get_api_client():
    """Get or initialize the API client (lazy loading)."""
    global _api_client
    if _api_client is None:
        try:
            from src.client.scrapper_api_client import ScrapperAPIClient

            _api_client = ScrapperAPIClient()
            logger.info("API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize API client: {e}")
            raise
    return _api_client


@ai_bp.route("/api/ai/health", methods=["GET"])
def health():
    """Health check for AI analyzer."""
    try:
        analyzer = get_analyzer()
        provider_type = type(analyzer.provider).__name__
        return jsonify({"status": "ok", "provider": provider_type, "ready": True}), 200
    except Exception as e:
        logger.warning(f"Health check failed: {e}")
        return jsonify({"status": "error", "error": str(e), "ready": False}), 503


@ai_bp.route("/api/ai/analyze", methods=["POST"])
def analyze_events():
    """Analyze economic events using LLM."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        analysis_request = AnalysisRequest(**data)
        logger.info(f"Received analysis request: {analysis_request}")

    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        return jsonify({"error": f"Invalid request: {str(e)}"}), 400
    except Exception as e:
        logger.warning(f"Request parsing failed: {e}")
        return jsonify({"error": "Request format error"}), 400

    example_count = data.get("example_count", 0)
    response_style = data.get("response_style")

    try:
        if example_count is None:
            example_count = 0
        else:
            example_count = int(example_count)
            if example_count < 0:
                raise ValueError("example_count must be >= 0")
    except Exception as e:
        return jsonify({"error": f"Invalid example_count: {e}"}), 400

    allowed_styles = {"concise", "detailed", "step_by_step", "balanced"}
    if response_style:
        if not isinstance(response_style, str) or response_style not in allowed_styles:
            return (
                jsonify(
                    {
                        "error": (
                                "Invalid response_style. Allowed values: "
                                + ", ".join(sorted(allowed_styles))
                        )
                    }
                ),
                400,
            )

    try:
        analyzer = get_analyzer()
        result = analyzer.analyze(
            request=analysis_request,
            example_count=example_count,
            response_style=response_style
        )
        return jsonify({
            "reply": result.summary,
            "analysis": result.model_dump(),
            "provider": type(analyzer.provider).__name__,
            "analysis_request": analysis_request.model_dump(),
        }), 200

    except ValueError as e:
        logger.warning(f"Analysis validation error: {e}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 400
    except Exception as e:
        logger.exception(f"Unexpected error during analysis: {e}")
        return (
            jsonify(
                {
                    "error": "Analysis failed due to server error",
                    "detail": str(e) if logger.level == logging.DEBUG else None,
                }
            ),
            500,
        )


@ai_bp.route("/api/ai/chat", methods=["POST"])
def chat():
    """Chat-style endpoint that integrates intent parsing, scraping, and evaluation."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be valid JSON"}), 400
    except Exception as e:
        logger.warning(f"Invalid JSON: {e}")
        return jsonify({"error": "Request must be valid JSON"}), 400

    history = data.get("history", [])
    message = data.get("message")
    if not message or not isinstance(message, str):
        return jsonify({"error": "'message' field required and must be a string"}), 400

    try:
        parser = get_intent_parser()
        parsed_intent = parser.parse(message, today=date.today())
        logger.info(f"Parsed intent: {parsed_intent}")
    except Exception as e:
        logger.warning(f"Intent parsing failed, falling back to chat: {e}")
        return jsonify(FAILED_ANALYZE_CONVERSATION_RESPONSE_EN), 200

    # Handle general conversation intent
    if parsed_intent.intent == "chat":
        logger.info(f"Chat intent: {parsed_intent}")
        reply = parsed_intent.chat_response or "How can I assist you with economic events today?"
        return jsonify({
            "reply": reply,
            "analysis": None,
            "provider": type(parser.provider).__name__,
            "parsed_intent": parsed_intent.model_dump(),
            "events": None
        }), 200

    # Date range formatting and boundary constraints
    try:
        start_date, end_date, warning = validate_date_range(
            parsed_intent.start_date,
            parsed_intent.end_date,
            max_days=7
        )
        if warning:
            logger.warning(f"Date range warning: {warning}")
    except ValueError as e:
        logger.exception(f"Date range validation failed: {e}")
        return jsonify({"error": str(e)}), 400

    if not start_date or not end_date:
        start_date = end_date = date.today()

    sources = parsed_intent.sources if parsed_intent.sources else ["forex"]

    try:
        client = get_api_client()
        # LLM Token budget consideration for analysis
        # We can adjust this as needed
        max_event_limit = 50
        all_events = client.fetch_economic_data_bundle(
            sources=sources,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            limit=max_event_limit,
            offset=0
        )
    except Exception as e:
        logger.exception(f"Failed to fetch events from API client: {e}")
        return jsonify(SERVER_CONFIG_ERROR_EN), 500

    if not all_events or len(all_events) == 0:
        logger.exception(f"No events found for {start_date} to {end_date}")
        return jsonify(NO_EVENTS_FOUND_RESPONSE_EN), 200

    try:
        analysis_payload = {
            "events": all_events,
            "language": parsed_intent.language
        }
        if data.get("focus"):
            analysis_payload["focus"] = data.get("focus")
        example_count = int(data.get("example_count", 0) or 0)
        response_style = data.get("response_style")
        analysis_request = AnalysisRequest(**analysis_payload)
        logger.info(f"Analysis request created: {analysis_request}")
    except Exception as e:
        logger.warning(f"Invalid analysis payload: {e}")
        return jsonify({"error": f"Invalid analysis payload: {e}"}), 400

    try:
        analyzer = get_analyzer()
        result = analyzer.analyze(
            request=analysis_request,
            example_count=example_count,
            response_style=response_style
        )
        logger.info(f"Analysis result: {result.model_dump()}")
        return jsonify({
            "reply": result.summary,
            "analysis": result.model_dump(),
            "parsed_intent": parsed_intent.model_dump(),
            "provider": type(analyzer.provider).__name__,
            "events": all_events,
        }), 200

    except ValueError as e:
        logger.warning(f"Analysis validation error: {e}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 400
    except Exception as e:
        logger.exception(f"Unexpected error during chat analysis: {e}")
        return jsonify({
            "error": "Analysis failed due to server error",
            "detail": str(e) if logger.level == logging.DEBUG else None,
        }), 500
