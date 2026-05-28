# LLM-Based Intent Parsing — Implementation Guide

## Overview

The chat engine utilizes a sophisticated NLU intent parser powered by LLM function calling (or raw structured output). This system dynamically determines user intent from natural language, decides if economic calendar/volatility data needs to be fetched, resolves relative dates, maps currency sectors to sources, and handles fallback conversational chat.

---

## 🏗️ Architecture Flow

```
[ User Prompt ] ---> [ /api/ai/chat Endpoint ] 
                              |
                     [ NLU IntentParser ]
                              |
            +-----------------+-----------------+
            |                                   |
    [ Intent: chat ]                   [ Intent: fetch_data ]
            |                                   |
   [ Direct Conversational ]          [ Extract sources, date boundaries ]
   [ Response in User Lang ]                    |
                                      [ Fetch data via ScrapperClient ]
                                                |
                                      [ Run Volatility Analysis (LLM) ]
                                                |
                                      [ Return Summary + Raw Events ]
```

### Components

#### 1. `src/ai/intent_parser.py`
Facilitates LLM provider loading and provides the clean `.parse(message, today)` facade.

*   `ParsedIntent` (Pydantic model) - Structured representation of intent, sources, start_date, end_date, chat response, confidence, and detected language.
*   `OllamaIntentParserProvider` - Handles structured output formatting for local Ollama.
*   `GroqIntentParserProvider` / `OpenAIIntentParserProvider` - Employs native function calling tools (`fetch_economic_data`) for maximum reliability.

#### 2. Date Boundary Resolution
The intent system automatically parses relative keywords in the user's prompt into ISO date boundaries relative to the evaluation day:
*   "today" / "bugün" -> `YYYY-MM-DD` (Today)
*   "yesterday" / "dün" -> `YYYY-MM-DD` (Yesterday)
*   "tomorrow" / "yarın" -> `YYYY-MM-DD` (Tomorrow)
*   "this week" / "bu hafta" -> Monday of this week to Today
*   "last week" / "geçen hafta" -> Monday of last week to Sunday of last week
*   "last week Wednesday" -> Specific date matching Wednesday of last week.

#### 3. Data Source Mapping
Maps natural currency keywords to scraped bundle sources:
*   "forex", "döviz", "usd", "eur", "currencies" -> `["forex"]`
*   "crypto", "kripto", "bitcoin", "solana" -> `["crypto"]`
*   "metal", "metals", "altın", "gold", "silver" -> `["metal"]`
*   "energy", "enerji", "petrol", "oil", "gas" -> `["energy"]`

---

## 📡 API Usage & Interactive Flow

Because dates and sources are extracted dynamically by the NLU system from the conversation text, client requests do not need to supply static date parameters! This allows for a completely natural conversational UI.

### 1. General Conversation
*   **Endpoint**: `POST /api/ai/chat`
*   **Request Payload**:
    ```json
    {
      "message": "Merhaba! Yardımcı olabilir misin?"
    }
    ```
*   **Response** (200 OK):
    ```json
    {
      "reply": "Merhaba! Tabii ki, ekonomik takvim verilerini veya piyasa analizlerini incelemenize yardımcı olabilirim.",
      "analysis": null,
      "parsed_intent": {
        "intent_type": "chat",
        "chat_response": "Merhaba! Tabii ki...",
        "confidence": 0.90,
        "reasoning": "Greeting keyword matched",
        "language": "tr",
        "sources": [],
        "start_date": null,
        "end_date": null
      },
      "provider": "OllamaIntentParserProvider",
      "events": null
    }
    ```

### 2. Fetch and Analyze Data Query
*   **Endpoint**: `POST /api/ai/chat`
*   **Request Payload**:
    ```json
    {
      "message": "Bugün Forex piyasalarında ne oldu?",
      "focus": "trading"
    }
    ```
*   **Response** (200 OK):
    ```json
    {
      "reply": "The market sentiment is neutral today following minor USD adjustments...",
      "analysis": {
        "summary": "The market sentiment is neutral today...",
        "analyses": [
          {
            "event_name": "FOMC Minutes",
            "currency": "USD",
            "time": "2026-05-28 14:00:00",
            "expectation_vs_previous": "Balanced forecast...",
            "actual_vs_expectation": "Aligned with expectation...",
            "market_implication": "USD remains stable...",
            "sentiment": "neutral",
            "confidence": "high"
          }
        ],
        "overall_sentiment": "neutral",
        "key_events": ["FOMC Minutes"],
        "risk_level": "low"
      },
      "parsed_intent": {
        "intent_type": "fetch_data",
        "chat_response": null,
        "confidence": 0.95,
        "reasoning": "User requested economic calendar data for today",
        "language": "en",
        "sources": ["forex"],
        "start_date": "2026-05-28",
        "end_date": "2026-05-28"
      },
      "provider": "GroqProvider",
      "events": [
        {
          "ID": "1",
          "Time": "2026-05-28 14:00:00",
          "Currency": "USD",
          "Event": "FOMC Minutes",
          "Forecast": "n/a",
          "Actual": "n/a",
          "Previous": "n/a",
          "Impact": "high"
        }
      ]
    }
    ```

---

## 🔧 Decoupled Fallback Mode
If your configured LLM API is unavailable, the system automatically falls back to the `SimpleIntentParser` (rule-based keyword parser) without throwing hard exceptions, providing robust offline resiliency.

---

## 🧪 Testing Intent NLU Locally
To run verification suite on parser limits and routing controllers:
```bash
PYTHONPATH=. .venv/bin/pytest -v
```
