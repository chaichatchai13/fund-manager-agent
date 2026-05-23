"""
Social intel skill — X (Twitter) account watchlist management and social signal summaries.
Delegates to app.services.social_service (to be implemented).
"""
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "get_social_watchlist",
        "description": "List all X (Twitter) accounts in the watchlist with their tracked stocks.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "add_social_watchlist",
        "description": "Add X accounts to watch for specific stocks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x_handle": {"type": "string", "description": "X handle without @, e.g. 'unusual_whales'"},
                "stocks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ticker symbols to track for this account",
                },
            },
            "required": ["x_handle", "stocks"],
        },
    },
    {
        "name": "get_social_summary",
        "description": "Get a summary of recent posts from watched X accounts for specific stocks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stocks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by these tickers. Empty = all watched stocks.",
                },
                "since_last_check": {"type": "boolean", "default": True},
            },
            "required": [],
        },
    },
]

_TOOL_NAMES = {t["name"] for t in TOOL_DEFINITIONS}


async def handle_tool_call(name: str, tool_input: dict[str, Any]) -> Any:
    """Handle a social-intel tool call. Returns None if name is not owned by this skill."""
    if name not in _TOOL_NAMES:
        return None

    try:
        from app.services.social_service import social_service

        if name == "get_social_watchlist":
            return await social_service.get_watchlist()

        if name == "add_social_watchlist":
            return await social_service.add_to_watchlist(tool_input["x_handle"], tool_input["stocks"])

        if name == "get_social_summary":
            return await social_service.get_summary(
                stocks=tool_input.get("stocks", []),
                since_last_check=tool_input.get("since_last_check", True),
            )

    except Exception as exc:
        logger.error("Social intel tool handler error", tool=name, error=str(exc))
        return {"error": str(exc)}

    return None
