from unittest.mock import MagicMock, patch
import pytest
from flask import json
from src.app import app
from src.ai.schemas import EconomicAnalysisResult, IntentParsingResult, FetchEconomicDataParams

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_root_route(client):
    """Verify root route returns UI HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"<!doctype html>" in response.data or b"chat" in response.data.lower()

def test_hello_route(client):
    """Verify health sub-route /api/hello returns success."""
    response = client.get("/api/hello")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Hello, World!"
    assert data["status"] == "success"

def test_health_route(client):
    """Verify liveness health check."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "ok"

@patch("src.routes.ai_routes.get_analyzer")
def test_ai_health_route(mock_get_analyzer, client):
    """Verify AI health endpoint details and success status."""
    mock_analyzer = MagicMock()
    mock_analyzer.provider = MagicMock()
    type(mock_analyzer.provider).__name__ = "MockLLMProvider"
    mock_get_analyzer.return_value = mock_analyzer
    
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "ok"
    assert data["provider"] == "MockLLMProvider"
    assert data["ready"] is True

def test_analyze_endpoint_missing_payload(client):
    """Verify 400 bad request on missing request payload."""
    response = client.post("/api/ai/analyze", json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data

@patch("src.routes.ai_routes.get_analyzer")
def test_analyze_endpoint_success(mock_get_analyzer, client):
    """Test successful event analysis workflow."""
    mock_analyzer = MagicMock()
    mock_get_analyzer.return_value = mock_analyzer
    
    # Mock analysis result
    mock_result = EconomicAnalysisResult(
        summary="Events analyzed successfully.",
        analyses=[],
        overall_sentiment="neutral",
        key_events=[],
        risk_level="low"
    )
    mock_analyzer.analyze.return_value = mock_result
    
    payload = {
        "events": [
            {
                "ID": "1",
                "Time": "2026-05-21 14:30:00",
                "Currency": "USD",
                "Event": "NFP",
                "Forecast": "150k",
                "Actual": "145k",
                "Previous": "140k",
                "Impact": "high"
            }
        ],
        "language": "en"
    }
    
    response = client.post("/api/ai/analyze", json=payload)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "reply" in data
    assert "analysis" in data
    assert data["reply"] == "Events analyzed successfully."
    assert data["analysis"]["overall_sentiment"] == "neutral"

@patch("src.routes.ai_routes.get_intent_parser")
def test_chat_endpoint_general_chat(mock_get_intent_parser, client):
    """Test chat endpoint routing to simple conversational chat response."""
    mock_parser = MagicMock()
    mock_get_intent_parser.return_value = mock_parser
    
    # Return chat intent
    mock_intent = IntentParsingResult(
        intent_type="chat",
        confidence=0.9,
        reasoning="Simple conversation",
        language="tr",
        chat_response="Nasılsınız?"
    )
    mock_parser.parse.return_value = mock_intent
    
    payload = {"message": "Selam, nasılsın?"}
    response = client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["reply"] == "Nasılsınız?"
    assert data["analysis"] is None

@patch("src.routes.ai_routes.get_analyzer")
@patch("src.routes.ai_routes.get_api_client")
@patch("src.routes.ai_routes.get_intent_parser")
def test_chat_endpoint_fetch_data(mock_get_intent_parser, mock_get_api_client, mock_get_analyzer, client):
    """Test chat endpoint triggering scrapper fetching and analysis flow."""
    mock_parser = MagicMock()
    mock_get_intent_parser.return_value = mock_parser
    
    mock_api_client = MagicMock()
    mock_get_api_client.return_value = mock_api_client
    
    mock_analyzer = MagicMock()
    mock_get_analyzer.return_value = mock_analyzer
    
    # Mock data-fetching intent
    mock_intent = IntentParsingResult(
        intent_type="fetch_data",
        confidence=0.95,
        reasoning="User queried data",
        language="en",
        fetch_params=FetchEconomicDataParams(
            sources=["forex"],
            start_date="2026-05-24",
            end_date="2026-05-25",
            language="en"
        )
    )
    mock_parser.parse.return_value = mock_intent
    
    # Mock fetched events from scrapper API client
    mock_api_client.fetch_economic_data_bundle.return_value = [
        {
            "ID": "1",
            "Time": "2026-05-24 10:00:00",
            "Currency": "EUR",
            "Event": "German Ifo Business Climate",
            "Forecast": "89.0",
            "Actual": "89.3",
            "Previous": "88.6",
            "Impact": "medium"
        }
    ]
    
    # Mock economic analysis
    mock_result = EconomicAnalysisResult(
        summary="Fetched calendar data showing neutral growth.",
        analyses=[],
        overall_sentiment="neutral",
        key_events=[],
        risk_level="low"
    )
    mock_analyzer.analyze.return_value = mock_result
    
    payload = {"message": "Show me forex events for today"}
    response = client.post("/api/ai/chat", json=payload)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["reply"] == "Fetched calendar data showing neutral growth."
    assert data["analysis"]["overall_sentiment"] == "neutral"
    assert len(data["events"]) == 1
    assert data["events"][0]["Currency"] == "EUR"
