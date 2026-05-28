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

## 🏗️ Architecture Overview

### Components

```
├── src/ai/
│   ├── __init__.py
│   ├── schemas.py        # Pydantic models (Input/Output)
│   └── analyzer.py       # LLM providers & analysis engine
├── src/routes/
│   └── ai_routes.py      # Flask endpoints
└── tests/
    └── test_ai_analyzer.py  # Unit tests
```

### Architecture Highlights

✅ **Pydantic Structured Output**: Validate LLM outputs against schemas

✅ **Flexible LLM Providers**: Support for Ollama, Groq, OpenAI

✅ **Clean Code**: SOLID principles and a provider pattern using abstract methods

✅ **Lazy Loading**: LLM libraries are imported only when needed

✅ **Environment Config**: Easy configuration via a `.env` file

## 🚀 Installation

### 1. Install required libraries

```bash
# Core requirements are already listed in requirements.txt:
pip install pydantic requests

# Optional provider libraries (install as needed):
# For Groq:
pip install groq

# For OpenAI:
pip install openai
```

### 2. Ollama setup (Development)

```bash
# macOS
brew install ollama

# Other OS: https://ollama.ai/download

# Start Ollama server
ollama serve

# In another terminal, pull a model
ollama pull qwen:7b  # or llama2, mistral, etc.
```

## ⚙️ Configuration

### Create a `.env` file

```bash
# Copy the example file
cp .env.example.ai .env
```

### Option 1: Ollama (Local)

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen:7b
```

### Option 2: Groq (Cloud)

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=mixtral-8x7b-32768
```

### Option 3: OpenAI (Cloud)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
```

## 📡 API Endpoints

### 1. Analyze Economic Events

**Endpoint**: `POST /api/ai/analyze`

**Request Body**:
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
  "focus": "trading"
}
```

**Response** (200 OK):
```json
{
  "summary": "Weaker-than-expected NFP data is creating selling pressure on the dollar.",
  "analyses": [
    {
      "event_name": "Non-Farm Payrolls",
      "currency": "USD",
      "time": "2026-05-21 14:30:00",
      "expectation_vs_previous": "Forecast: 150k, Previous: 140k (+7.1% increase expected)",
      "actual_vs_expectation": "Actual: 145k vs Forecast: 150k (-3.3% miss)",
      "market_implication": "Weaker than expected jobs data may reduce Fed hiking probabilities",
      "sentiment": "neutral",
      "confidence": "high"
    }
  ],
  "overall_sentiment": "neutral",
  "key_events": ["Non-Farm Payrolls"],
  "risk_level": "medium"
}
```

**Query Parameters**:
- `language` (optional, default: "en"): Response language (en, tr, fr, etc.)
- `focus` (optional): Focus area for analysis (trading, investment, macro)

### 2. Health Check

**Endpoint**: `GET /api/ai/health`

**Response** (200 OK):
```json
{
  "status": "ok",
  "provider": "OllamaProvider",
  "ready": true
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "error",
  "error": "Connection refused",
  "ready": false
}
```

## 📊 Examples

### Python client example

```python
import requests

# Call the API
response = requests.post(
    "http://localhost:5000/api/ai/analyze",
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
print(f"Summary: {result['summary']}")
print(f"Overall Sentiment: {result['overall_sentiment']}")
print(f"Risk Level: {result['risk_level']}")

# Detailed analysis
for analysis in result['analyses']:
    print(f"\n{analysis['event_name']} ({analysis['currency']})")
    print(f"  Sentiment: {analysis['sentiment']}")
    print(f"  Confidence: {analysis['confidence']}")
```

### cURL example

```bash
curl -X POST http://localhost:5000/api/ai/analyze \
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

### Scraper integration example

```python
from src.scrapper.forexFactoryScrapper import get_records, get_url
from src.ai.analyzer import EconomicAnalyzer
from src.ai.schemas import AnalysisRequest

# 1. Fetch events from the scraper
url = get_url(day=21, month=5, year=2026)
events = get_records(url)  # Returns list of dicts

# 2. Run LLM analysis
analyzer = EconomicAnalyzer()  # Provider loaded from .env
request = AnalysisRequest(
    events=events,
    language="tr",
    focus="trading"
)
analysis_result = analyzer.analyze(request)

# 3. Use results
print(f"Summary: {analysis_result.summary}")
print(f"Key Events: {', '.join(analysis_result.key_events)}")
```

## 🤖 LLM Providers

### Ollama (Local)

**Advantages**:
- ✅ Works offline
- ✅ Privacy (data stays local)
- ✅ Free
- ✅ GPU support

**Drawbacks**:
- ❌ Slower inference compared to cloud high-performance APIs
- ❌ Models may be smaller or less capable

**Setup**:
```bash
brew install ollama
ollama serve
ollama pull qwen:7b
```

**Models**:
- `qwen:7b` - Multilingual, fast
- `llama2` - General purpose
- `mistral` - High-quality
- `neural-chat` - Chat-optimized

### Groq (Cloud)

**Advantages**:
- ✅ Very fast inference
- ✅ Low latency and cost
- ✅ No heavy local setup

**Drawbacks**:
- ❌ Internet required
- ❌ API key required

**Setup**:
```bash
pip install groq
# Obtain API key from: https://console.groq.com
```

### OpenAI (Cloud)

**Advantages**:
- ✅ Most capable models (GPT-4)
- ✅ Broad language support
- ✅ Reliable API

**Drawbacks**:
- ❌ Higher cost
- ❌ Internet required

**Setup**:
```bash
pip install openai
# Obtain an API key: https://platform.openai.com/api-keys
```

## 🐳 Docker Deployment

### Update Dockerfile

Update your existing `Dockerfile` as follows:

```dockerfile
# ... existing instructions ...

# Add AI libraries
RUN pip install pydantic requests

# (Optional) Cloud providers
# RUN pip install groq openai

# Ollama support (optional)
# RUN apt-get install -y curl && \
#     curl https://ollama.ai/install.sh | sh
```

### docker-compose.yml (with Ollama)

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
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

**Start**:
```bash
docker-compose up
```

## 🧪 Testing

### Run unit tests

```bash
pytest tests/test_ai_analyzer.py -v
```

### Integration test

```bash
# 1. Start the app
python main.py

# 2. In another terminal, run a test request
curl -X POST http://localhost:5000/api/ai/analyze \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

## 📚 Schema Reference

### AnalysisRequest

```python
{
    "events": [
        {
            "ID": str,              # Event ID
            "Time": str,            # Format: YYYY-MM-DD HH:MM:SS
            "Currency": str,        # USD, EUR, GBP, etc.
            "Event": str,           # Event name
            "Forecast": str,        # Forecast value
            "Actual": str,          # Actual value (n/a if not released)
            "Previous": str,        # Previous period value
            "Impact": str           # low, medium, high, n/a
        }
    ],
    "language": str,                # default: "en"
    "focus": str | null             # Optional: trading, investment, macro
}
```

### EconomicAnalysisResult

```python
{
    "summary": str,                 # 2-3 sentence overview
    "analyses": [
        {
            "event_name": str,
            "currency": str,
            "time": str,
            "expectation_vs_previous": str,      # Analysis
            "actual_vs_expectation": str | null, # null = not yet released
            "market_implication": str,
            "sentiment": str,       # bullish, neutral, bearish
            "confidence": str       # low, medium, high
        }
    ],
    "overall_sentiment": str,       # bullish, neutral, bearish
    "key_events": [str],            # Top 3-5 events
    "risk_level": str               # low, medium, high
}
```

## 🔧 Troubleshooting

### "ConnectionError: Cannot connect to Ollama"

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running:
ollama serve
```

### "GROQ_API_KEY required"

```bash
# Verify API key in your .env
echo $GROQ_API_KEY
```

### LLM output fails schema

- Inspect the prompt sent to the LLM
- Try a different model or provider
- Check logs in DEBUG mode: `DEBUG=True`

## 📝 Notes

- All LLM providers validate the JSON output automatically
- Response language can be configured via the `.env` file
- Custom prompts are configurable in `analyzer.py`
