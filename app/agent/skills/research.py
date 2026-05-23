"""
Research skill — web search and stock news retrieval.
Delegates to app.services.research_service (to be implemented).
"""
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": "Search the web for information about stocks, news, analyst opinions, earnings, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query, e.g. 'TSLA earnings Q1 2026 analyst targets'"},
                "count": {"type": "integer", "default": 5, "description": "Number of results to return (max 10)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_stock_news",
        "description": "Search for recent news articles about a specific stock ticker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "days_back": {"type": "integer", "default": 7},
            },
            "required": ["symbol"],
        },
    },
]

_TOOL_NAMES = {t["name"] for t in TOOL_DEFINITIONS}


async def handle_tool_call(name: str, tool_input: dict[str, Any]) -> Any:
    """Handle a research tool call. Returns None if name is not owned by this skill."""
    if name not in _TOOL_NAMES:
        return None

    try:
        from app.services.research_service import research_service

        if name == "web_search":
            results = await research_service.search(tool_input["query"], count=tool_input.get("count", 5))
            return results

        if name == "search_stock_news":
            results = await research_service.search_news(
                tool_input["symbol"], days_back=tool_input.get("days_back", 7)
            )
            return results

    except Exception as exc:
        logger.error("Research tool handler error", tool=name, error=str(exc))
        return {"error": str(exc)}

    return None
