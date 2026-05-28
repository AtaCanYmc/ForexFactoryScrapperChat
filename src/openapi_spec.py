# Minimal OpenAPI spec shared across the app
OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "ForexFactoryScrapper LLM Chat",
        "version": "1.0.0",
        "description": "OpenAPI spec with schemas for the scraping and AI analysis API",
        "contact": {"name": "Repo maintainer", "email": "atacanymc@gmail.com"},
        "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    },
    # Helpful servers entry for local development
    "servers": [{"url": "http://localhost:8080", "description": "Local dev server"}],
    "tags": [
        {"name": "health", "description": "Health and misc endpoints"},
        {"name": "ai", "description": "LLM analysis endpoints"},
    ],
    "paths": {
        "/": {
            "get": {
                "summary": "Root welcome page",
                "tags": ["health"],
                "responses": {"200": {"description": "HTML welcome page"}},
            }
        },
        "/api/hello": {
            "get": {
                "summary": "Hello endpoint",
                "tags": ["health"],
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/api/health": {
            "get": {
                "summary": "Health check",
                "tags": ["health"],
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/api/ai/analyze": {
            "post": {
                "summary": "Analyze economic events using LLM",
                "tags": ["ai"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "events": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/Record"
                                        },
                                    },
                                    "language": {"type": "string", "default": "en"},
                                    "focus": {"type": ["string", "null"]},
                                    "example_count": {"type": "integer", "minimum": 0, "default": 0},
                                    "response_style": {
                                        "type": "string",
                                        "description": "Preferred response style",
                                        "enum": [
                                            "concise",
                                            "detailed",
                                            "step_by_step",
                                            "balanced",
                                        ],
                                    },
                                },
                                "required": ["events"],
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Structured economic analysis result",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/AnalyzeResponse"
                                }
                            }
                        },
                    },
                    "400": {
                        "description": "Bad Request - validation error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                    "500": {
                        "description": "Server error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                },
            }
        },
        "/api/ai/chat": {
            "post": {
                "summary": "Chat endpoint: ask conversational questions about economic events",
                "tags": ["ai"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "message": {"type": "string", "description": "Conversational question or prompt about economic data"},
                                    "focus": {"type": ["string", "null"], "description": "Optional analysis focus"},
                                    "example_count": {"type": "integer", "minimum": 0, "default": 0},
                                    "response_style": {
                                        "type": "string",
                                        "description": "Preferred response style",
                                        "enum": [
                                            "concise",
                                            "detailed",
                                            "step_by_step",
                                            "balanced",
                                        ],
                                    },
                                },
                                "required": ["message"],
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Conversational reply and optional structured analysis",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ChatResponse"
                                }
                            }
                        },
                    },
                    "400": {
                        "description": "Bad Request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                    "500": {
                        "description": "Server error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                },
            }
        },
        "/api/ai/health": {
            "get": {
                "summary": "AI analyzer health check",
                "tags": ["ai"],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "503": {
                        "description": "Service Unavailable",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                },
            }
        },
    },
    "components": {
        "schemas": {
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "description": "Error message"}
                },
                "required": ["error"],
            },
            "Record": {
                "type": "object",
                "properties": {
                    "ID": {"type": ["string", "null"], "description": "Unique identifier of the event"},
                    "Time": {"type": "string", "description": "Time of the event in format YYYY-MM-DD HH:MM:SS"},
                    "Currency": {"type": ["string", "null"], "default": "n/a", "description": "Currency code"},
                    "Event": {"type": "string", "description": "Name of the event"},
                    "Forecast": {"type": "string", "description": "Expected value"},
                    "Actual": {"type": "string", "description": "Actual value if released"},
                    "Previous": {"type": "string", "description": "Previous period value"},
                    "Impact": {"type": ["string", "null"], "description": "Impact level (low, medium, high, n/a)"},
                    "_date": {"type": "string", "description": "Event Date format YYYY-MM-DD"},
                    "_source": {"type": "string", "description": "Source name (e.g. forex, crypto)"}
                },
                "required": ["Time", "Event", "Forecast", "Actual", "Previous"]
            },
            "EventAnalysis": {
                "type": "object",
                "properties": {
                    "event_name": {"type": "string"},
                    "currency": {"type": ["string", "null"]},
                    "time": {"type": "string"},
                    "expectation_vs_previous": {"type": "string"},
                    "actual_vs_expectation": {
                        "oneOf": [{"type": "string"}, {"type": "null"}]
                    },
                    "market_implication": {"type": "string"},
                    "sentiment": {
                        "type": "string",
                        "enum": ["bullish", "neutral", "bearish"],
                    },
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": [
                    "event_name",
                    "time",
                    "expectation_vs_previous",
                    "market_implication",
                    "sentiment",
                    "confidence",
                ],
            },
            "EconomicAnalysisResult": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "analyses": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/EventAnalysis"},
                    },
                    "overall_sentiment": {
                        "type": "string",
                        "enum": ["bullish", "neutral", "bearish"],
                    },
                    "key_events": {"type": "array", "items": {"type": "string"}},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": [
                    "summary",
                    "analyses",
                    "overall_sentiment",
                    "key_events",
                    "risk_level",
                ],
            },
            "AnalyzeResponse": {
                "type": "object",
                "properties": {
                    "reply": {"type": "string", "description": "Summary of the analysis"},
                    "analysis": {"$ref": "#/components/schemas/EconomicAnalysisResult"},
                    "provider": {"type": "string", "description": "Name of the LLM provider"},
                    "analysis_request": {
                        "type": "object",
                        "properties": {
                            "events": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Record"}
                            },
                            "language": {"type": "string"},
                            "focus": {"type": ["string", "null"]}
                        },
                        "required": ["events"]
                    }
                },
                "required": ["reply", "analysis", "provider", "analysis_request"]
            },
            "ChatResponse": {
                "type": "object",
                "properties": {
                    "reply": {"type": "string", "description": "Response text or economic analysis summary"},
                    "analysis": {
                        "oneOf": [
                            {"$ref": "#/components/schemas/EconomicAnalysisResult"},
                            {"type": "null"}
                        ]
                    },
                    "parsed_intent": {
                        "type": "object",
                        "properties": {
                            "intent_type": {"type": "string", "enum": ["fetch_data", "chat"]},
                            "intent": {"type": "string"},
                            "fetch_params": {
                                "oneOf": [
                                    {
                                        "type": "object",
                                        "properties": {
                                            "sources": {"type": "array", "items": {"type": "string"}},
                                            "start_date": {"type": "string", "format": "date"},
                                            "end_date": {"type": "string", "format": "date"},
                                            "language": {"type": "string"}
                                        },
                                        "required": ["sources", "start_date", "end_date"]
                                    },
                                    {"type": "null"}
                                ]
                            },
                            "chat_response": {"type": ["string", "null"]},
                            "confidence": {"type": "number"},
                            "reasoning": {"type": "string"},
                            "language": {"type": "string"},
                            "sources": {"type": "array", "items": {"type": "string"}},
                            "start_date": {"type": ["string", "null"], "format": "date"},
                            "end_date": {"type": ["string", "null"], "format": "date"}
                        },
                        "required": ["intent_type", "confidence", "reasoning", "language"]
                    },
                    "provider": {"type": "string", "description": "LLM Provider name"},
                    "events": {
                        "oneOf": [
                            {"type": "array", "items": {"$ref": "#/components/schemas/Record"}},
                            {"type": "null"}
                        ]
                    }
                },
                "required": ["reply", "analysis", "parsed_intent", "provider", "events"]
            }
        }
    },
}
