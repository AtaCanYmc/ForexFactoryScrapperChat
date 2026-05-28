# Minimal OpenAPI spec shared across the app
OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "ForexFactoryScrapper LLM Chat",
        "version": "1.0.0",
        "description": "OpenAPI spec with schemas for the scraping API",
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
                                    "example_count": {"type": "integer", "minimum": 0},
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
                                    "$ref": "#/components/schemas/EconomicAnalysisResult"
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
                                    "message": {"type": "string"},
                                    "history": {
                                        "type": "array",
                                        "items": {"type": "object"},
                                    },
                                    "source": {
                                        "type": "string",
                                        "description": (
                                            "Optional data source filter: "
                                            "forex, cryptocraft, metalsmine, energyexch"
                                        ),
                                    },
                                    "start_date": {"type": "string", "format": "date"},
                                    "end_date": {"type": "string", "format": "date"},
                                },
                                "required": ["message"],
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Conversational reply and optional structured analysis",
                        "content": {"application/json": {"schema": {"type": "object"}}},
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
            "EventAnalysis": {
                "type": "object",
                "properties": {
                    "event_name": {"type": "string"},
                    "currency": {"type": "string"},
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
                    "currency",
                    "time",
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
        }
    },
}
