"""
Schemas for LLM response validation and structuring.
"""

CONTENT_ANALYSIS_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "content_analysis",
        "schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "context": {
                    "type": "string",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["keywords", "context", "tags"],
            "additionalProperties": False
        },
        "strict": True
    }
}

MEMORY_EVOLUTION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "memory_evolution",
        "schema": {
            "type": "object",
            "properties": {
                "should_evolve": {"type": "boolean"},
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["strengthen", "update_neighbor", "contradict"]
                    }
                },
                "suggested_connections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {"type": "string", "enum": ["support", "contradict"]},
                            "reason": {"type": "string"}
                        },
                        "required": ["id", "type", "reason"],
                        "additionalProperties": False
                    }
                },
                "new_context_neighborhood": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "tags_to_update": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "new_tags_neighborhood": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "required": [
                "should_evolve", "actions", "suggested_connections",
                "tags_to_update", "new_context_neighborhood", "new_tags_neighborhood"
            ],
            "additionalProperties": False
        },
        "strict": True
    }
}
