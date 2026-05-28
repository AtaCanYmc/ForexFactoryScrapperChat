# AI Economic Event Analysis - Integration Guide

This guide shows how to integrate LLM-based economic event analysis into your Flask API.

## 📋 Contents

1. [Architecture Overview](#architecture-overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [API Endpoints](#api-endpoints)
5. [Examples](#examples)
6. [LLM Providers](#llm-providers)
7. [Docker Deployment](#docker-deployment)
8. [Testing](#testing)

---

## 🏗️ Architecture Overview

### Components

```
├── src/ai/
│   ├── __init__.py
│   ├── schemas.py        # Pydantic models (Input/Output)
│   ├── analyzer.py       # LLM providers & analysis engine orchestrator
│   └── providers/        # LLM specific drivers (Ollama, Groq, OpenAI)
├── src/routes/
│   └── ai_routes.py      # Flask endpoints
└── tests/
    └── test_routes.py    # Controller integration tests
```

### Architecture Highlights

✅ **Pydantic Structured Output**: Validate LLM outputs against schemas.

✅ **Flexible LLM Providers**: Seamless support for Ollama, Groq, OpenAI.

✅ **Clean Code**: SOLID principles and a provider pattern using abstract methods.

✅ **Lazy Loading**: LLM libraries (like groq, openai) are imported only when needed.

✅ **Environment Config**: Easy configuration via a `.env` file.

---

## 🚀 Installation

### 1. Install required libraries

```bash
# Core requirements are already listed in requirements.txt:
pip install pydantic requests

# Optional provider libraries (install as needed for your cloud choice):
# For Groq:
pip install groq

# For OpenAI:
pip install openai
```

### 2. Ollama setup (Development / Offline)

```bash
# macOS
brew install ollama

# Other OS: https://ollama.ai/download

# Start Ollama server
ollama serve

# In another terminal, pull a model
ollama pull qwen:7b  # or llama2, mistral, etc.
```

---

## ⚙️ Configuration

### Create a `.env` file

```bash
# Copy the example file
cp .env.example .env
```

### Option 1: Ollama (Local)

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen:7b
```

### Option 2: Groq (Cloud - Fast Inference)

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=mixtral-8x7b-32768
```

### Option 3: OpenAI (Cloud - Production)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
```

---

## 📡 API Endpoints

### 1. Analyze Economic Events

*   **Endpoint**: `POST /api/ai/analyze`
*   **Request Body**:
    ```json
    {
      "events": [
        {
          "ID": "12345",
          "Time": "2026-05-21 14:30:00",
          "Currency": "USD",
          "Event": "Non-Farm Payrolls",
          "Forecast": "150,000",
          "Actual": "145,000",
          "Previous": "140,000",
          "Impact": "high"
        }
      ],
      "language": "en",
      "focus": "trading",
      "example_count": 0,
      "response_style": "detailed"
    }
    ```

*   **Response Wrapper** (200 OK):
    ```json
    {
      "reply": "Weaker-than-expected NFP data is creating selling pressure on the dollar.",
      "analysis": {
        "summary": "Weaker-than-expected NFP data is creating selling pressure on the dollar.",
        "analyses": [
          {
            "event_name": "Non-Farm Payrolls",
            "currency": "USD",
            "time": "2026-05-21 14:30:00",
            "expectation_vs_previous": "Forecast: 150k, Previous: 140k (+7.1% increase expected)",
            "actual_vs_expectation": "Actual: 145k vs Forecast: 150k (-3.3% miss)",
            "market_implication": "Weaker than expected jobs data may reduce Fed hiking probabilities",
            "sentiment": "bearish",
            "confidence": "high"
          }
        ],
        "overall_sentiment": "bearish",
        "key_events": ["Non-Farm Payrolls"],
        "risk_level": "medium"
      },
      "provider": "OllamaProvider",
      "analysis_request": {
        "events": [ ... ],
        "language": "en",
        "focus": "trading"
      }
    }
    ```

### 2. Health Check

*   **Endpoint**: `GET /api/ai/health`
*   **Response** (200 OK):
    ```json
    {
      "status": "ok",
      "provider": "OllamaProvider",
      "ready": true
    }
    ```
*   **Response** (503 Service Unavailable):
    ```json
    {
      "status": "error",
      "error": "Connection refused",
      "ready": false
    }
    ```

---

## 📊 Examples

### Python client example

```python
import requests

# Call the API on default port 8080
response = requests.post(
    "http://localhost:8080/api/ai/analyze",
    json={
        "events": [
            {
                "ID": "1",
                "Time": "2026-05-21 14:30:00",
                "Currency": "USD",
                "Event": "Non-Farm Payrolls",
                "Forecast": "150k",
                "Actual": "145k",
                "Previous": "140k",
                "Impact": "high",
            }
        ],
        "language": "tr",
        "focus": "trading"
    }
)

result = response.json()
print(f"Summary: {result['reply']}")
print(f"Provider Used: {result['provider']}")

# Detailed analysis
analysis_details = result['analysis']
print(f"Overall Sentiment: {analysis_details['overall_sentiment']}")
print(f"Risk Level: {analysis_details['risk_level']}")

for analysis in analysis_details['analyses']:
    print(f"\n{analysis['event_name']} ({analysis['currency']})")
    print(f"  Sentiment: {analysis['sentiment']}")
    print(f"  Confidence: {analysis['confidence']}")
```

### cURL example

```bash
curl -X POST http://localhost:8080/api/ai/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "ID": "1",
        "Time": "2026-05-21 14:30:00",
        "Currency": "USD",
        "Event": "Non-Farm Payrolls",
        "Forecast": "150k",
        "Actual": "145k",
        "Previous": "140k",
        "Impact": "high"
      }
    ],
    "language": "en"
  }'
```

---

## 🤖 LLM Providers

### Ollama (Local)
*   **Advantages**: Offline execution, privacy-first, free, local GPU acceleration.
*   **Setup**:
    ```bash
    brew install ollama
    ollama serve
    ollama pull qwen:7b
    ```

### Groq (Cloud)
*   **Advantages**: Very low latency, lightning-fast inference, Mixtral model capabilities.
*   **Setup**: Get API key from [Groq Console](https://console.groq.com).

### OpenAI (Cloud)
*   **Advantages**: Advanced logic parsing, broad language accuracy, GPT-4 availability.
*   **Setup**: Get API key from [OpenAI Platform](https://platform.openai.com).

---

## 🐳 Docker Deployment

### docker-compose.yml (with Ollama integration)

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - LLM_PROVIDER=ollama
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=qwen:7b
      - DEBUG=False
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    command: serve

volumes:
  ollama_data:
```

---

## 🧪 Testing

### Run automated tests
To test date structures, schema validation, and route mock controller layers:
```bash
PYTHONPATH=. .venv/bin/pytest -v
```
