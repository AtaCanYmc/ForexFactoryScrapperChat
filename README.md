# ForexFactoryScrapper LLM Chat

An institutional-grade, AI-powered conversational assistant and economic event analyzer. This system combines real-time data scraping pipelines (covering forex, cryptocurrencies, metals, and energy) with state-of-the-art Large Language Models (LLMs) to deliver structured, action-oriented financial analysis directly to traders and investors.

---

## 🚀 Key Features

*   **Intelligent Intent Parsing (NLU)**: Leverages LLM function calling (or raw structured output) to determine if a query requires economic calendar data. Routes automatically between conversational chat and targeted data scraping.
*   **Decoupled Scraping Client**: Fully integrated with the decoupled `ForexFactoryScrapper` bundle API supporting multi-source querying (`forex`, `crypto`, `metal`, `energy`).
*   **Pydantic Structured Outputs**: Guarantees JSON schema compliance for LLM analysis, eliminating raw text hallucination risks and securing downstream parsing.
*   **Flexible LLM Provider Engine**: Fully abstract provider layer allows seamless switching between:
    *   **Local Inference**: Self-hosted Ollama (e.g. `Qwen`, `Llama`, `Mistral`).
    *   **Cloud Inference**: Groq API (superfast inference) or OpenAI API (`GPT-4`).
*   **Calibrated Volatility Analytics**: Provides traders with market sentiment (`bullish`, `bearish`, `neutral`), trading implications, confidence levels, key event priorities, and macroeconomic summaries.
*   **Robust Date Range Validation**: Validates natural dates (e.g., "today", "yesterday", "last week Wednesday") and clamps query limits to a maximum of 7 days to prevent rate limits and performance bottlenecks.
*   **Aesthetic Swagger UI & Interactive Chat**: Provides beautiful built-in Swagger specification endpoints (`/swagger`) and a premium web-based glassmorphism chat UI (`/`).

---

## 🏗️ Architecture Overview

The system adheres strictly to decoupled, clean-code architecture principles:

```
├── main.py                 # Application launcher
├── requirements.txt        # Package dependencies
├── src/
│   ├── app.py              # Flask server setup, CORS & Blueprints
│   ├── openapi_spec.py     # OpenAPI specification schemas
│   ├── middleware.py       # Lifecycle handlers (correlation ID propagation)
│   ├── client/
│   │   ├── schemas.py      # Scrapper API models (Pydantic)
│   │   └── scrapper_api_client.py # HTTPX client for the scraping engine
│   ├── ai/
│   │   ├── ai_constants.py # AI system limits, supported languages, fallback configs
│   │   ├── ai_utils.py     # System prompt rendering & structured output parsers
│   │   ├── exceptions.py   # Domain-specific NLU exceptions
│   │   ├── intent_parser.py# NLU orchestrator facade
│   │   ├── analyzer.py     # Analysis engine orchestrator facade
│   │   ├── prompts/        # Jinja2-templated prompts
│   │   ├── intent/         # Rule-based fallback parser & function specifications
│   │   └── providers/      # LLM provider implementations (Ollama, Groq, OpenAI)
│   ├── routes/
│   │   ├── ai_routes.py    # AI analyze & NLU chat controllers
│   │   ├── swagger_routes.py # Swagger UI endpoint & specification delivery
│   │   └── root_routes.py  # Interactive Chat UI view
│   └── templates/
│       └── chat.html       # Premium glassmorphic chat front-end
└── tests/                  # Robust Pytest suite
```

---

## ⚙️ Configuration & Environment Setup

Copy the example environment file and customize it for your setup:
```bash
cp .env.example .env
```

### Option 1: Local Ollama (Offline / Privacy-first)
Make sure [Ollama](https://ollama.ai) is running locally, then pull a fast multilingual model:
```bash
ollama pull qwen:7b
```
Configure your `.env`:
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen:7b
```

### Option 2: Groq Cloud API (Lightning-fast Cloud Inference)
Obtain an API key from the [Groq Console](https://console.groq.com):
```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_api_key
GROQ_MODEL=mixtral-8x7b-32768
```

### Option 3: OpenAI API (Gold Standard Analysis)
Obtain an API key from the [OpenAI Platform](https://platform.openai.com):
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-your_openai_api_key
OPENAI_MODEL=gpt-4-turbo-preview
```

---

## 🚀 Quick Start Guide

### 1. Installation
Create and activate a python virtual environment, then install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Running Locally
Run the Flask server:
```bash
python main.py
```
The server will boot by default on `http://127.0.0.1:8080`.

*   **Interactive Web Chat UI**: Navigate to `http://127.0.0.1:8080/`
*   **Swagger API Docs**: Navigate to `http://127.0.0.1:8080/swagger`
*   **Raw OpenAPI Spec**: Navigate to `http://127.0.0.1:8080/openapi.json`

---

## 📡 API Endpoints Specifications

### 1. Analyze Scraped Events
*   **Path**: `POST /api/ai/analyze`
*   **Description**: Sends raw events to the LLM to get structured volatility summaries.
*   **Request Body**:
    ```json
    {
      "events": [
        {
          "ID": "123",
          "Time": "2026-05-21 14:30:00",
          "Currency": "USD",
          "Event": "Non-Farm Payrolls",
          "Forecast": "150k",
          "Actual": "145k",
          "Previous": "140k",
          "Impact": "high"
        }
      ],
      "language": "tr",
      "focus": "trading",
      "example_count": 0,
      "response_style": "detailed"
    }
    ```
*   **Response Wrapper** (200 OK):
    ```json
    {
      "reply": "Institutional high-level macro summary of the events...",
      "analysis": {
        "summary": "High-level summary for investors...",
        "analyses": [
          {
            "event_name": "Non-Farm Payrolls",
            "currency": "USD",
            "time": "2026-05-21 14:30:00",
            "expectation_vs_previous": "Missed forecast...",
            "actual_vs_expectation": "Negative implication...",
            "market_implication": "USD under pressure...",
            "sentiment": "bearish",
            "confidence": "high"
          }
        ],
        "overall_sentiment": "bearish",
        "key_events": ["Non-Farm Payrolls"],
        "risk_level": "medium"
      },
      "provider": "GroqProvider",
      "analysis_request": { ... }
    }
    ```

### 2. NLU Conversational Chat
*   **Path**: `POST /api/ai/chat`
*   **Description**: Analyzes natural query text, fetches relevant market data if needed, and replies.
*   **Request Body**:
    ```json
    {
      "message": "Geçen hafta Çarşamba günü Forex'te ne oldu?",
      "focus": "macro",
      "response_style": "concise"
    }
    ```

---

## 🧪 Testing Suite

We maintain a high-coverage unit and integration test suite targeting utilities, schema validation, LLM providers, and controllers.

To execute tests with proper path resolution, run:
```bash
PYTHONPATH=. .venv/bin/pytest -v
```

---

## 🐳 Docker Deployment

To launch the app with a companion containerized local Ollama server, use `docker-compose`:

```bash
docker-compose up --build
```
This starts both the Flask application and the Ollama instance in the same virtual network, allowing secure, fast local inference.
