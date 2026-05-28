# LLM-Based Intent Parsing — Implementation Guide

## Overview

We've implemented a sophisticated intent parsing system using LLM function calling (tool use) to intelligently extract user intent, data sources, and date ranges from natural language. The system intelligently routes between:

1. **Fetch Data** - User asking about economic events/data
2. **Chat** - General conversation that doesn't require data fetching

## Architecture

### Components

#### 1. `src/ai/intent_parser.py`
Main intent parsing module with support for multiple LLM providers.

**Key Classes:**
- `ParsedIntent` (Pydantic model) - Structured result with intent, sources, start_date, end_date
- `IntentParserProvider` (ABC) - Abstract base for provider implementations
- `OllamaIntentParser` - Local LLM support (Qwen, Llama, etc.)
- `GroqIntentParser` - Groq cloud API support
- `OpenAIIntentParser` - OpenAI API support
- `IntentParser` - Main orchestrator (lazy-loads appropriate provider)

**Helper Functions:**
- `validate_date_range()` - Validates dates and enforces max 7-day limit

#### 2. `src/routes/ai_routes.py` (Updated)
Chat endpoint (`POST /api/ai/chat`) now uses `IntentParser` for intelligent routing.

**Flow:**
1. User sends message
2. `get_intent_parser()` parses intent via LLM function calling
3. If intent is "chat" → respond conversationally
4. If intent is "fetch_data" → extract sources/dates, fetch events, analyze

#### 3. Tool Definition (Function Calling)
The `fetch_economic_data` tool signature (used by Groq/OpenAI):
```json
{
  "type": "function",
  "function": {
    "name": "fetch_economic_data",
    "description": "Fetch economic calendar data from specified sources and date range",
    "parameters": {
      "type": "object",
      "properties": {
        "sources": {
          "type": "array",
          "items": {"type": "string", "enum": ["forex", "cryptocraft", "metalsmine", "energyexch"]}
        },
        "start_date": {"type": "string", "description": "YYYY-MM-DD"},
        "end_date": {"type": "string", "description": "YYYY-MM-DD"}
      },
      "required": ["sources", "start_date", "end_date"]
    }
  }
}
```

Ollama uses structured output with the same JSON schema.

## Setup & Configuration

### 1. Environment Variables

Choose one LLM provider:

#### Ollama (Local, Self-Hosted)
```bash
export LLM_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=qwen:7b  # or llama2, neural-chat, etc.
```

#### Groq (Cloud)
```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY=gsk_...
export GROQ_MODEL=mixtral-8x7b-32768  # optional
```

#### OpenAI (Cloud)
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4-turbo-preview  # optional
```

### 2. Install Dependencies

For Groq/OpenAI support, install the respective libraries:

```bash
# Groq
pip install groq>=0.4.1

# OpenAI
pip install openai>=1.0.0

# Ollama support is built-in (uses requests)
```

### 3. Start Ollama (if using local)

```bash
# On macOS (Homebrew)
brew install ollama
ollama serve

# In another terminal, pull a model
ollama pull qwen:7b
```

Or download from https://ollama.ai

## Usage

### Programmatic (Python)

```python
from datetime import date
from src.ai.intent_parser import IntentParser, validate_date_range

# Initialize parser (auto-detects provider from environment)
parser = IntentParser()

# Parse a user message
user_message = "Geçen hafta Çarşamba Forex'te ne oldu?"
parsed_intent = parser.parse(user_message, today=date.today())

print(parsed_intent.intent)       # "fetch_data"
print(parsed_intent.sources)      # ["forex"]
print(parsed_intent.start_date)   # "2026-05-21"
print(parsed_intent.end_date)     # "2026-05-21"
print(parsed_intent.reasoning)    # "User asked about specific day in past week"

# Validate date range (enforces max 7-day limit)
start, end, warning = validate_date_range("2026-05-10", "2026-05-30", max_days=7)
# Returns: ("2026-05-10", "2026-05-17", "Date range (20 days) exceeds limit (7 days)...")
```

### Via Chat API

```bash
# General chat (no data fetch)
curl -X POST http://localhost:5000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Selam! Nasılsın?"}'

# Fetch economic data
curl -X POST http://localhost:5000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Bugün önemli Forex verileri açıklandı mı?",
    "source": "forex"
  }'

# Override with explicit dates
curl -X POST http://localhost:5000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Kripto piyasalarında neler oldu?",
    "source": "cryptocraft",
    "start_date": "2026-05-23",
    "end_date": "2026-05-24"
  }'
```

## Testing

### Unit Tests (Date Validation)

```bash
python test_intent_parser.py
```

Expected output:
```
✓ 7-day range OK: 2026-05-20 to 2026-05-27
✓ Range capped: 2026-05-10 to 2026-05-17
✓ Correctly rejected: Invalid date format...
✓ Valid intent: fetch_data
✓ IntentParser initialized: OllamaIntentParser
```

### Integration Tests (With Real LLM)

```bash
# Requires Ollama running (or other LLM provider configured)
python test_intent_integration.py
```

This will parse real test messages and display structured results.

## Design Decisions

1. **Multiple Provider Support**: Users can choose local (Ollama) or cloud (Groq/OpenAI) based on needs.

2. **Function Calling via Tool Use**: LLM determines whether to call `fetch_economic_data` tool or respond conversationally. This is more accurate than rule-based parsing.

3. **Date Range Capping**: Maximum 7-day limit prevents excessive scraper calls and API usage.

4. **Lazy Initialization**: Parsers are initialized on first use to avoid startup delays.

5. **Structured Output Schema**: `ParsedIntent` Pydantic model ensures type safety and validation.

6. **Fallback Handling**: If parsing fails, chat endpoint gracefully degrades with helpful message.

## Common Issues & Troubleshooting

### Issue: "Connection refused" on Ollama
**Solution**: Ensure Ollama is running on the configured URL:
```bash
# Check if running
curl http://localhost:11434/api/tags

# Start if not running
ollama serve
```

### Issue: "GROQ_API_KEY required"
**Solution**: Set environment variable:
```bash
export GROQ_API_KEY=gsk_...
```

### Issue: Long response times with intent parsing
**Reason**: First request to LLM is slow. Subsequent requests are cached by lazy initialization.
**Solution**: For production, consider pre-warming the parser on startup.

## Future Enhancements

1. **Streaming Responses**: Return intent parsing results as they arrive (SSE/WebSocket)
2. **Fallback to Rule-Based**: If LLM unavailable, automatically use simple regex parsing
3. **Intent Caching**: Cache parsed intents for identical/similar messages
4. **Custom System Prompts**: Allow fine-tuning of LLM behavior per deployment
5. **Multi-Provider Failover**: Try Groq, fallback to Ollama if unavailable
6. **Metrics & Logging**: Track intent accuracy, parsing time, error rates

## Related Files

- **Intent Parsing**: `src/ai/intent_parser.py`
- **Chat Endpoint**: `src/routes/ai_routes.py` (updated `/api/ai/chat`)
- **Chat UI**: `src/templates/chat.html` (with localStorage history)
- **Tests**: `test_intent_parser.py`, `test_intent_integration.py`
- **OpenAPI Spec**: Updated in `src/openapi_spec.py`
